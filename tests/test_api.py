import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from agents.base import AgentRun
from db.database import Base, get_db

SAMPLE_TRANSCRIPT = (Path(__file__).parent / "sample_transcript.txt").read_text(encoding="utf-8")

EXTRACTED = {
    "title": "Project Kickoff and Timeline Review",
    "action_items": [
        {"text": "Finish the authentication module", "assignee": "John"},
        {"text": "Set up the staging environment", "assignee": "John"},
        {"text": "Put together the test cases", "assignee": "Mike"},
        {"text": "Book the review room", "assignee": None},
    ],
}
SUMMARY = {
    "overview": "Kickoff meeting for the upcoming project.",
    "key_points": ["API mostly complete", "Mobile designs in progress"],
    "decisions": "Reconvene next Wednesday at 2pm.",
}
EMAIL = {"subject": "Follow-up on Project Kickoff", "body": "Hi team,\n\n..."}


def agent_run(data, model="gpt-4o-mini"):
    return AgentRun(data=data, model=model, seconds=0.5, prompt_tokens=1000, completion_tokens=200)


@pytest.fixture
def calls():
    return {"drafter": [], "reminder": []}


@pytest.fixture
def client(monkeypatch, calls):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    async def fake_extractor(transcript):
        return agent_run(EXTRACTED, model="gpt-4o")

    async def fake_summarizer(transcript):
        return agent_run(SUMMARY)

    async def fake_drafter(items, summary=None):
        calls["drafter"].append((items, summary))
        return agent_run(EMAIL)

    async def fake_reminder(assignee, action_items, meeting_title):
        calls["reminder"].append((assignee, action_items, meeting_title))
        return agent_run({"subject": f"Reminder for {assignee}", "body": "..."})

    monkeypatch.setattr(main, "run_extractor", fake_extractor)
    monkeypatch.setattr(main, "run_summarizer", fake_summarizer)
    monkeypatch.setattr(main, "run_email_drafter", fake_drafter)
    monkeypatch.setattr(main, "run_reminder_drafter", fake_reminder)
    main.app.dependency_overrides[get_db] = override_get_db

    yield TestClient(main.app)

    main.app.dependency_overrides.clear()


def process(client):
    res = client.post("/meetings/process", json={"transcript": SAMPLE_TRANSCRIPT})
    assert res.status_code == 200
    return res.json()


def stream_events(res):
    return [json.loads(line[len("data: "):]) for line in res.text.splitlines() if line.startswith("data: ")]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_process_rejects_short_transcript(client):
    res = client.post("/meetings/process", json={"transcript": "   too short   "})

    assert res.status_code == 400
    assert "at least 50 characters" in res.json()["detail"]


def test_process_returns_and_saves_results(client, calls):
    data = process(client)

    assert data["meeting"]["title"] == EXTRACTED["title"]
    assert data["summary"] == SUMMARY
    assert data["email_draft"] == EMAIL
    assert [i["text"] for i in data["action_items"]] == [i["text"] for i in EXTRACTED["action_items"]]
    assert all(i["status"] == "pending" for i in data["action_items"])
    assert calls["drafter"][0] == (EXTRACTED["action_items"], SUMMARY)

    meetings = client.get("/meetings").json()
    assert len(meetings) == 1
    assert meetings[0]["summary"] == SUMMARY
    assert len(meetings[0]["action_items"]) == 4


def test_process_reports_per_agent_metrics(client):
    metrics = process(client)["metrics"]

    assert set(metrics["agents"]) == {"extractor", "summarizer", "email_drafter"}
    assert metrics["agents"]["extractor"]["model"] == "gpt-4o"
    expected_cost = sum(a["cost_usd"] for a in metrics["agents"].values())
    assert metrics["cost_usd"] == pytest.approx(expected_cost)
    assert metrics["total_seconds"] >= 0


def test_extractor_and_summarizer_run_in_parallel(client, monkeypatch):
    summarizer_started = asyncio.Event()

    async def extractor_waiting_for_summarizer(transcript):
        # Only completes if the summarizer is running at the same time
        await asyncio.wait_for(summarizer_started.wait(), timeout=2)
        return agent_run(EXTRACTED, model="gpt-4o")

    async def summarizer_signalling_start(transcript):
        summarizer_started.set()
        return agent_run(SUMMARY)

    monkeypatch.setattr(main, "run_extractor", extractor_waiting_for_summarizer)
    monkeypatch.setattr(main, "run_summarizer", summarizer_signalling_start)

    assert process(client)["summary"] == SUMMARY


def test_stream_reports_progress_then_result(client):
    res = client.post("/meetings/process/stream", json={"transcript": SAMPLE_TRANSCRIPT})

    assert res.headers["content-type"].startswith("text/event-stream")
    events = stream_events(res)
    progress = [(e["agent"], e["status"]) for e in events if e["type"] == "agent"]
    assert set(progress[:2]) == {("extractor", "running"), ("summarizer", "running")}
    assert set(progress[2:4]) == {("extractor", "done"), ("summarizer", "done")}
    assert progress[4:] == [("email_drafter", "running"), ("email_drafter", "done")]
    assert all("seconds" in e for e in events if e.get("status") == "done")
    assert events[-1]["type"] == "result"
    assert events[-1]["data"]["meeting"]["title"] == EXTRACTED["title"]


def test_stream_rejects_short_transcript(client):
    assert client.post("/meetings/process/stream", json={"transcript": "short"}).status_code == 400


def test_agent_failure_returns_502_and_saves_nothing(client, monkeypatch):
    async def failing_extractor(transcript):
        raise RuntimeError("OpenAI is down")

    monkeypatch.setattr(main, "run_extractor", failing_extractor)

    res = client.post("/meetings/process", json={"transcript": SAMPLE_TRANSCRIPT})

    assert res.status_code == 502
    assert "extractor agent failed" in res.json()["detail"]
    assert client.get("/meetings").json() == []


def test_agent_failure_is_streamed_as_error_event(client, monkeypatch):
    async def failing_drafter(items, summary=None):
        raise TimeoutError()

    monkeypatch.setattr(main, "run_email_drafter", failing_drafter)

    res = client.post("/meetings/process/stream", json={"transcript": SAMPLE_TRANSCRIPT})

    events = stream_events(res)
    assert events[-1] == {"type": "error", "detail": "The email drafter agent failed: TimeoutError"}
    assert client.get("/meetings").json() == []


def test_update_action_item_status_and_text(client):
    item_id = process(client)["action_items"][0]["id"]

    res = client.patch(f"/action-items/{item_id}", params={"status": "done"})
    assert res.json()["status"] == "done"

    res = client.patch(f"/action-items/{item_id}", params={"text": "Finish OAuth login"})
    assert res.json() == {
        "id": item_id, "text": "Finish OAuth login", "assignee": "John", "status": "done"
    }


def test_update_unknown_action_item_returns_404(client):
    assert client.patch("/action-items/999", params={"status": "done"}).status_code == 404


def test_add_action_item(client):
    meeting_id = process(client)["meeting"]["id"]

    res = client.post("/action-items", params={
        "meeting_id": meeting_id, "text": "Email the client", "assignee": "Sarah"
    })

    assert res.json()["assignee"] == "Sarah"
    assert len(client.get("/meetings").json()[0]["action_items"]) == 5


def test_remind_all_groups_pending_items_by_assignee(client):
    data = process(client)
    meeting_id = data["meeting"]["id"]
    mike_item = next(i for i in data["action_items"] if i["assignee"] == "Mike")
    client.patch(f"/action-items/{mike_item['id']}", params={"status": "done"})

    res = client.post(f"/meetings/{meeting_id}/remind-all")

    body = res.json()["body"]
    assert res.json()["subject"] == f"Reminder: Outstanding action items — {EXTRACTED['title']}"
    assert "John:\n  - Finish the authentication module\n  - Set up the staging environment" in body
    assert "Team:\n  - Book the review room" in body
    assert "Put together the test cases" not in body


def test_remind_all_with_nothing_pending_returns_404(client):
    data = process(client)
    for item in data["action_items"]:
        client.patch(f"/action-items/{item['id']}", params={"status": "done"})

    assert client.post(f"/meetings/{data['meeting']['id']}/remind-all").status_code == 404


def test_remind_single_assignee_is_case_insensitive(client, calls):
    meeting_id = process(client)["meeting"]["id"]

    res = client.post(f"/meetings/{meeting_id}/remind/john")

    assert res.json() == {"subject": "Reminder for john", "body": "..."}
    assignee, items, title = calls["reminder"][0]
    assert [i["text"] for i in items] == [
        "Finish the authentication module", "Set up the staging environment"
    ]
    assert title == EXTRACTED["title"]


def test_remind_unknown_assignee_returns_404(client):
    meeting_id = process(client)["meeting"]["id"]

    assert client.post(f"/meetings/{meeting_id}/remind/Zoe").status_code == 404


def test_regenerate_email_uses_current_item_state(client, calls):
    data = process(client)
    item_id = data["action_items"][0]["id"]
    client.patch(f"/action-items/{item_id}", params={"status": "done"})

    res = client.post(f"/meetings/{data['meeting']['id']}/regenerate-email")

    assert res.json() == EMAIL
    items, summary = calls["drafter"][-1]
    assert items[0]["status"] == "done"
    assert summary == SUMMARY


def test_delete_meeting(client):
    meeting_id = process(client)["meeting"]["id"]

    assert client.delete(f"/meetings/{meeting_id}").json() == {"success": True}
    assert client.get("/meetings").json() == []
    assert client.delete(f"/meetings/{meeting_id}").status_code == 404
