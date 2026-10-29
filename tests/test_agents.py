import asyncio

from agents import base, email_drafter, extractor, reminder_drafter, summarizer
from agents.base import AgentRun
from conftest import crew_task
from models.schemas import EmailDraft, ExtractedActionItem, ExtractionOutput, SummaryOutput


def run(coro):
    return asyncio.run(coro)


# Extractor

def test_extractor_returns_structured_output(fake_crew):
    crew_cls = fake_crew(
        ExtractionOutput(title="Sprint Planning", action_items=[{"text": "Write tests", "assignee": "Mike"}]),
        prompt_tokens=1200, completion_tokens=150,
    )

    result = run(extractor.run_extractor("John: let's plan the sprint..."))

    assert result.data == {"title": "Sprint Planning", "action_items": [{"text": "Write tests", "assignee": "Mike"}]}
    assert result.fallback is False
    assert result.model == "gpt-4o"
    assert (result.prompt_tokens, result.completion_tokens) == (1200, 150)
    assert crew_task(crew_cls).output_pydantic is ExtractionOutput
    crew_cls.return_value.kickoff_async.assert_awaited_once()


def test_extractor_includes_transcript_in_prompt(fake_crew):
    crew_cls = fake_crew(ExtractionOutput(title="T", action_items=[]))

    run(extractor.run_extractor("Priya: I'll send the mockups Thursday."))

    assert "Priya: I'll send the mockups Thursday." in crew_task(crew_cls).description


def test_extractor_model_can_be_overridden(fake_crew):
    crew_cls = fake_crew(ExtractionOutput(title="T", action_items=[]))

    result = run(extractor.run_extractor("transcript", model="gpt-4o-mini"))

    assert result.model == "gpt-4o-mini"
    assert crew_cls.call_args.kwargs["agents"][0].llm.model == "gpt-4o-mini"


def test_extractor_falls_back_when_output_fails_validation(fake_crew):
    fake_crew(parsed=None)

    result = run(extractor.run_extractor("some transcript"))

    assert result.data == {"title": "Untitled Meeting", "action_items": []}
    assert result.fallback is True


def test_blank_assignees_are_normalised_to_none():
    for value in ["null", "None", "", "  ", "Unassigned"]:
        assert ExtractedActionItem(text="Do it", assignee=value).assignee is None
    assert ExtractedActionItem(text="Do it", assignee=" Dana ").assignee == "Dana"


# Summarizer

def test_summarizer_returns_structured_output(fake_crew):
    crew_cls = fake_crew(SummaryOutput(
        overview="Kickoff meeting.", key_points=["API nearly done"], decisions="Reconvene Wednesday."
    ))

    result = run(summarizer.run_summarizer("transcript"))

    assert result.data["overview"] == "Kickoff meeting."
    assert result.model == "gpt-4o-mini"
    assert crew_task(crew_cls).output_pydantic is SummaryOutput


def test_summarizer_falls_back_when_output_fails_validation(fake_crew):
    fake_crew(parsed=None)

    result = run(summarizer.run_summarizer("transcript"))

    assert result.data == {"overview": "Summary unavailable", "key_points": [], "decisions": ""}
    assert result.fallback is True


# Email drafter

def test_email_drafter_skips_llm_when_no_action_items(fake_crew):
    crew_cls = fake_crew(EmailDraft(subject="x", body="y"))

    result = run(email_drafter.run_email_drafter([]))

    crew_cls.assert_not_called()
    assert result.data["subject"] == "Meeting Summary"
    assert result.cost_usd == 0


def test_email_drafter_separates_pending_and_done_items(fake_crew):
    crew_cls = fake_crew(EmailDraft(subject="Follow-up", body="Hi team"))
    items = [
        {"text": "Finish auth module", "assignee": "John", "status": "pending"},
        {"text": "Homepage designs", "assignee": "Priya", "status": "done"},
        {"text": "Book a room", "assignee": None, "status": "pending"},
    ]

    result = run(email_drafter.run_email_drafter(items, {"overview": "Kickoff meeting."}))

    prompt = crew_task(crew_cls).description
    assert "- Finish auth module (Assignee: John)" in prompt
    assert "- Book a room (Assignee: Unassigned)" in prompt
    assert "Completed items:" in prompt and "- Homepage designs" in prompt
    assert "Meeting overview: Kickoff meeting." in prompt
    assert result.data == {"subject": "Follow-up", "body": "Hi team"}


def test_email_drafter_fallback_lists_pending_items(fake_crew):
    fake_crew(parsed=None)
    items = [{"text": "Set up staging", "assignee": "John", "status": "pending"}]

    result = run(email_drafter.run_email_drafter(items))

    assert result.data["subject"] == "Meeting Follow-up: Action Items"
    assert "Set up staging (Assignee: John)" in result.data["body"]


# Reminder drafter

def test_reminder_drafter_targets_assignee(fake_crew):
    crew_cls = fake_crew(EmailDraft(subject="Reminder", body="Hi Mike"))

    result = run(reminder_drafter.run_reminder_drafter("Mike", [{"text": "Write test plan"}], "Project Kickoff"))

    prompt = crew_task(crew_cls).description
    assert "Mike" in prompt and "Project Kickoff" in prompt and "- Write test plan" in prompt
    assert result.data == {"subject": "Reminder", "body": "Hi Mike"}


def test_reminder_drafter_fallback(fake_crew):
    fake_crew(parsed=None)

    result = run(reminder_drafter.run_reminder_drafter("Priya", [{"text": "Mobile screens"}], "Design Review"))

    assert result.data["subject"] == "Quick reminder — your action items from Design Review"
    assert result.data["body"].startswith("Hi Priya,")


# Shared runner

def test_cost_is_computed_from_token_usage():
    run_4o = AgentRun(data={}, model="gpt-4o", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    run_mini = AgentRun(data={}, model="gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)

    assert run_4o.cost_usd == 12.50
    assert run_mini.cost_usd == 0.75
    assert AgentRun(data={}, model="unknown-model", prompt_tokens=100).cost_usd == 0


def test_models_can_be_configured_with_env_vars(monkeypatch):
    monkeypatch.setenv("SUMMARIZER_MODEL", "gpt-4o")

    assert base.model_for("summarizer") == "gpt-4o"
    assert base.model_for("extractor") == "gpt-4o"
    assert base.model_for("email_drafter") == "gpt-4o-mini"
