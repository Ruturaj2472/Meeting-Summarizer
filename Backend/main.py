from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db.database import init_db, get_db
from db import queries
from models.schemas import MeetingCreate
from agents.extractor import run_extractor
from agents.email_drafter import run_email_drafter
from agents.summarizer import run_summarizer
from agents.reminder_drafter import run_reminder_drafter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from collections import defaultdict
import asyncio
import json
import logging
import os
import time

logger = logging.getLogger("meeting_summarizer")

app = FastAPI(title="Meeting Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend static files (present in the Docker image)

if os.path.exists("static"):
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/", include_in_schema=False)
async def serve_root():
    if not os.path.exists("static/index.html"):
        return {"message": "Meeting Summarizer API. Docs at /docs; run the frontend with `npm run dev`."}
    return FileResponse("static/index.html")

@app.get("/favicon.svg", include_in_schema=False)
async def serve_favicon():
    return FileResponse("static/favicon.svg")

@app.on_event("startup")
def startup():
    init_db()

class AgentError(Exception):
    def __init__(self, agent: str, error: Exception):
        self.agent = agent
        super().__init__(f"The {agent.replace('_', ' ')} agent failed: {type(error).__name__}")

async def run_agent(name: str, coro):
    try:
        return await coro
    except Exception as error:
        logger.exception("Agent %s failed", name)
        raise AgentError(name, error) from error

def validate_transcript(transcript: str):
    if len(transcript.strip()) < 50:
        raise HTTPException(status_code=400, detail="Transcript too short. Please provide at least 50 characters.")

async def process_pipeline(transcript: str, db: Session):
    """Run the agent pipeline, yielding progress events as each agent finishes.

    The extractor and summarizer only need the transcript, so they run in
    parallel; the email drafter needs both of their outputs, so it runs last.
    The meeting is saved only after every agent has succeeded.
    """
    start = time.perf_counter()

    tasks = {
        asyncio.create_task(run_agent("extractor", run_extractor(transcript))): "extractor",
        asyncio.create_task(run_agent("summarizer", run_summarizer(transcript))): "summarizer",
    }
    for name in tasks.values():
        yield {"type": "agent", "agent": name, "status": "running"}

    runs = {}
    pending = set(tasks)
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                name = tasks[task]
                runs[name] = task.result()
                yield {"type": "agent", "agent": name, "status": "done", "seconds": round(runs[name].seconds, 2)}
    finally:
        for task in pending:
            task.cancel()

    extraction = runs["extractor"].data
    summary = runs["summarizer"].data
    action_items_data = extraction.get("action_items", [])

    yield {"type": "agent", "agent": "email_drafter", "status": "running"}
    runs["email_drafter"] = await run_agent("email_drafter", run_email_drafter(action_items_data, summary))
    yield {"type": "agent", "agent": "email_drafter", "status": "done", "seconds": round(runs["email_drafter"].seconds, 2)}

    db_meeting = queries.create_meeting(
        db,
        title=extraction.get("title") or "Untitled Meeting",
        transcript=transcript,
        summary=json.dumps(summary)
    )
    db_items = queries.create_action_items(db, meeting_id=db_meeting.id, items=action_items_data)

    metrics = {
        "total_seconds": round(time.perf_counter() - start, 2),
        "cost_usd": round(sum(run.cost_usd for run in runs.values()), 6),
        "agents": {name: run.metrics() for name, run in runs.items()},
    }
    logger.info("Processed meeting %s: %s", db_meeting.id, metrics)

    yield {
        "type": "result",
        "data": {
            "meeting": {
                "id": db_meeting.id,
                "title": db_meeting.title,
                "created_at": db_meeting.created_at.isoformat(),
            },
            "summary": summary,
            "action_items": [
                {
                    "id": item.id,
                    "text": item.text,
                    "assignee": item.assignee,
                    "status": item.status,
                }
                for item in db_items
            ],
            "email_draft": runs["email_drafter"].data,
            "metrics": metrics,
        }
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/meetings/process")
async def process_meeting(meeting: MeetingCreate, db: Session = Depends(get_db)):
    validate_transcript(meeting.transcript)
    try:
        async for event in process_pipeline(meeting.transcript, db):
            if event["type"] == "result":
                return event["data"]
    except AgentError as error:
        raise HTTPException(status_code=502, detail=str(error))

@app.post("/meetings/process/stream")
async def process_meeting_stream(meeting: MeetingCreate, db: Session = Depends(get_db)):
    """Same pipeline as /meetings/process, streamed as Server-Sent Events."""
    validate_transcript(meeting.transcript)

    async def events():
        try:
            async for event in process_pipeline(meeting.transcript, db):
                yield f"data: {json.dumps(event)}\n\n"
        except AgentError as error:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(error)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/meetings")
def get_meetings(db: Session = Depends(get_db)):
    meetings = queries.get_all_meetings(db)
    return [
        {
            "id": m.id,
            "title": m.title,
            "created_at": m.created_at.isoformat(),
            "summary": json.loads(m.summary) if m.summary else None,
            "action_items": [
                {
                    "id": i.id,
                    "text": i.text,
                    "assignee": i.assignee,
                    "status": i.status,
                }
                for i in queries.get_action_items_by_meeting(db, m.id)
            ]
        }
        for m in meetings
    ]

@app.patch("/action-items/{item_id}")
def update_action_item(item_id: int, text: str = None, status: str = None, db: Session = Depends(get_db)):
    item = queries.update_action_item(db, item_id=item_id, text=text, status=status)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return {
        "id": item.id,
        "text": item.text,
        "assignee": item.assignee,
        "status": item.status
    }

@app.post("/meetings/{meeting_id}/remind/{assignee}")
async def send_reminder(meeting_id: int, assignee: str, db: Session = Depends(get_db)):
    items = queries.get_action_items_by_meeting(db, meeting_id)

    assignee_items = [
        {"text": item.text}
        for item in items
        if item.assignee and item.assignee.lower() == assignee.lower()
        and item.status == "pending"
    ]

    if not assignee_items:
        raise HTTPException(
            status_code=404,
            detail=f"No pending action items found for {assignee}"
        )

    meeting = queries.get_meeting_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    try:
        run = await run_agent("reminder_drafter", run_reminder_drafter(
            assignee=assignee,
            action_items=assignee_items,
            meeting_title=meeting.title
        ))
    except AgentError as error:
        raise HTTPException(status_code=502, detail=str(error))

    return run.data

@app.delete("/meetings/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = queries.get_meeting_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    queries.delete_meeting(db, meeting_id)
    return {"success": True}

@app.post("/meetings/{meeting_id}/remind-all")
def remind_all(meeting_id: int, db: Session = Depends(get_db)):
    meeting = queries.get_meeting_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    items = queries.get_action_items_by_meeting(db, meeting_id)
    pending = [i for i in items if i.status == "pending"]

    if not pending:
        raise HTTPException(
            status_code=404,
            detail="No pending action items found"
        )

    grouped = defaultdict(list)
    for item in pending:
        assignee = item.assignee
        if not assignee or assignee == "null" or assignee.strip() == "":
            assignee = "Team"
        grouped[assignee].append(item.text)

    body_lines = [
        f"Hi team,\n\nHere's a reminder of all outstanding action items from our meeting: \"{meeting.title}\"\n"
    ]

    for assignee, tasks in grouped.items():
        body_lines.append(f"{assignee}:")
        for task in tasks:
            body_lines.append(f"  - {task}")
        body_lines.append("")

    body_lines.append("Please complete your tasks at your earliest convenience.\n\nThanks")

    return {
        "subject": f"Reminder: Outstanding action items — {meeting.title}",
        "body": "\n".join(body_lines)
    }

@app.post("/action-items")
def add_action_item(
    meeting_id: int,
    text: str,
    assignee: str = None,
    db: Session = Depends(get_db)
):
    items = queries.create_action_items(
        db,
        meeting_id=meeting_id,
        items=[{"text": text, "assignee": assignee}]
    )
    item = items[0]
    return {
        "id": item.id,
        "text": item.text,
        "assignee": item.assignee,
        "status": item.status
    }

@app.post("/meetings/{meeting_id}/regenerate-email")
async def regenerate_email(meeting_id: int, db: Session = Depends(get_db)):
    meeting = queries.get_meeting_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    items = queries.get_action_items_by_meeting(db, meeting_id)
    items_data = [
        {
            "text": i.text,
            "assignee": i.assignee,
            "status": i.status
        }
        for i in items
    ]

    summary = json.loads(meeting.summary) if meeting.summary else None
    try:
        run = await run_agent("email_drafter", run_email_drafter(items_data, summary))
    except AgentError as error:
        raise HTTPException(status_code=502, detail=str(error))

    return run.data
