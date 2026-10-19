from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db.database import init_db, get_db
from db import queries
from models.schemas import MeetingCreate, ProcessResponse, ActionItem
from agents.extractor import run_extractor
from agents.email_drafter import run_email_drafter
from agents.summarizer import run_summarizer
from agents.reminder_drafter import run_reminder_drafter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import json

app = FastAPI(title="Meeting Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes are defined above this point
# Frontend static files served below

if os.path.exists("static"):
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/", include_in_schema=False)
async def serve_root():
    return FileResponse("static/index.html")

@app.get("/favicon.svg", include_in_schema=False)
async def serve_favicon():
    return FileResponse("static/favicon.svg")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/meetings/process")
def process_meeting(meeting: MeetingCreate, db: Session = Depends(get_db)):
    if len(meeting.transcript.strip()) < 50:
        raise HTTPException(status_code=400, detail="Transcript too short. Please provide at least 50 characters.")

    result = run_extractor(meeting.transcript)
    action_items_data = result.get("action_items", [])
    title = result.get("title", "Untitled Meeting")

    summary = run_summarizer(meeting.transcript)
    summary_json = json.dumps(summary)

    db_meeting = queries.create_meeting(
        db,
        title=title,
        transcript=meeting.transcript,
        summary=summary_json
    )
    db_items = queries.create_action_items(db, meeting_id=db_meeting.id, items=action_items_data)
    email_draft = run_email_drafter(action_items_data, summary)

    return {
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
        "email_draft": email_draft
    }

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
def send_reminder(meeting_id: int, assignee: str, db: Session = Depends(get_db)):
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
    
    email = run_reminder_drafter(
        assignee=assignee,
        action_items=assignee_items,
        meeting_title=meeting.title
    )
    
    return email

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

    from collections import defaultdict
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
def regenerate_email(meeting_id: int, db: Session = Depends(get_db)):
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
    email_draft = run_email_drafter(items_data, summary)

    return email_draft