from agents import email_drafter, extractor, reminder_drafter, summarizer


def task_prompt(task_cls):
    return task_cls.call_args.kwargs["description"]


# Extractor

def test_extractor_parses_json_surrounded_by_text(fake_crew):
    fake_crew(extractor, 'Here you go:\n{"title": "Sprint Planning", "action_items": '
                         '[{"text": "Write tests", "assignee": "Mike"}]}\nDone.')

    result = extractor.run_extractor("John: let's plan the sprint...")

    assert result["title"] == "Sprint Planning"
    assert result["action_items"] == [{"text": "Write tests", "assignee": "Mike"}]


def test_extractor_includes_transcript_in_prompt(fake_crew):
    task_cls, _ = fake_crew(extractor, '{"title": "T", "action_items": []}')

    extractor.run_extractor("Priya: I'll send the mockups Thursday.")

    assert "Priya: I'll send the mockups Thursday." in task_prompt(task_cls)


def test_extractor_falls_back_on_invalid_json(fake_crew):
    fake_crew(extractor, "Sorry, I could not process that.")

    result = extractor.run_extractor("some transcript")

    assert result == {"title": "Untitled Meeting", "action_items": []}


def test_extractor_falls_back_on_malformed_json(fake_crew):
    fake_crew(extractor, '{"title": "Broken", "action_items": [}')

    result = extractor.run_extractor("some transcript")

    assert result["title"] == "Untitled Meeting"


# Summarizer

def test_summarizer_parses_summary(fake_crew):
    fake_crew(summarizer, '{"overview": "Kickoff meeting.", "key_points": ["API nearly done"], '
                          '"decisions": "Reconvene Wednesday."}')

    result = summarizer.run_summarizer("transcript")

    assert result["overview"] == "Kickoff meeting."
    assert result["key_points"] == ["API nearly done"]
    assert result["decisions"] == "Reconvene Wednesday."


def test_summarizer_falls_back_on_invalid_json(fake_crew):
    fake_crew(summarizer, "not json")

    result = summarizer.run_summarizer("transcript")

    assert result == {"overview": "Summary unavailable", "key_points": [], "decisions": ""}


# Email drafter

def test_email_drafter_skips_llm_when_no_action_items(fake_crew):
    _, crew_cls = fake_crew(email_drafter, '{"subject": "x", "body": "y"}')

    result = email_drafter.run_email_drafter([])

    crew_cls.assert_not_called()
    assert result["subject"] == "Meeting Summary"


def test_email_drafter_separates_pending_and_done_items(fake_crew):
    task_cls, _ = fake_crew(email_drafter, '{"subject": "Follow-up", "body": "Hi team"}')
    items = [
        {"text": "Finish auth module", "assignee": "John", "status": "pending"},
        {"text": "Homepage designs", "assignee": "Priya", "status": "done"},
        {"text": "Book a room", "assignee": None, "status": "pending"},
    ]

    result = email_drafter.run_email_drafter(items, {"overview": "Kickoff meeting."})

    prompt = task_prompt(task_cls)
    assert "- Finish auth module (Assignee: John)" in prompt
    assert "- Book a room (Assignee: Unassigned)" in prompt
    assert "Completed items:" in prompt and "- Homepage designs" in prompt
    assert "Meeting overview: Kickoff meeting." in prompt
    assert result == {"subject": "Follow-up", "body": "Hi team"}


def test_email_drafter_fallback_lists_pending_items(fake_crew):
    fake_crew(email_drafter, "garbage")
    items = [{"text": "Set up staging", "assignee": "John", "status": "pending"}]

    result = email_drafter.run_email_drafter(items)

    assert result["subject"] == "Meeting Follow-up: Action Items"
    assert "Set up staging (Assignee: John)" in result["body"]


# Reminder drafter

def test_reminder_drafter_targets_assignee(fake_crew):
    task_cls, _ = fake_crew(reminder_drafter, '{"subject": "Reminder", "body": "Hi Mike"}')

    result = reminder_drafter.run_reminder_drafter(
        "Mike", [{"text": "Write test plan"}], "Project Kickoff"
    )

    prompt = task_prompt(task_cls)
    assert "Mike" in prompt and "Project Kickoff" in prompt and "- Write test plan" in prompt
    assert result == {"subject": "Reminder", "body": "Hi Mike"}


def test_reminder_drafter_fallback(fake_crew):
    fake_crew(reminder_drafter, "no json here")

    result = reminder_drafter.run_reminder_drafter(
        "Priya", [{"text": "Mobile screens"}], "Design Review"
    )

    assert result["subject"] == "Quick reminder — your action items from Design Review"
    assert result["body"].startswith("Hi Priya,")
    assert "- Mobile screens" in result["body"]
