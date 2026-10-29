import json
from pathlib import Path

from scoring import aggregate_extraction, match_items, score_email, score_extraction, score_summary

DATASET = Path(__file__).resolve().parent.parent / "evals" / "dataset.json"


def test_items_match_on_keywords_one_to_one():
    gold = [
        {"text": "Fix the Safari bug", "assignee": "Leo", "keywords": ["safari"]},
        {"text": "Write regression tests", "assignee": "Kim", "keywords": ["regression"]},
    ]
    predicted = [
        {"text": "Leo to fix checkout on Safari", "assignee": "Leo"},
        {"text": "Also look at Safari layout", "assignee": "Leo"},
        {"text": "Update the roadmap", "assignee": "Max"},
    ]

    pairs = match_items(predicted, gold)

    assert [(g["assignee"], p["text"]) for g, p in pairs] == [("Leo", "Leo to fix checkout on Safari")]


def test_extraction_precision_recall_and_assignee_accuracy():
    gold = [
        {"assignee": "Dana Lee", "keywords": ["queue"]},
        {"assignee": None, "keywords": ["photographer"]},
        {"assignee": "Kim", "keywords": ["regression"]},
    ]
    predicted = [
        {"text": "Migrate to the message queue", "assignee": "Dana"},
        {"text": "Book a photographer", "assignee": "Maya"},
        {"text": "Rewrite auth in Go", "assignee": "Dana"},
    ]

    result = aggregate_extraction([score_extraction(predicted, gold)])

    assert result["precision"] == 2 / 3
    assert result["recall"] == 2 / 3
    assert result["assignee_accuracy"] == 1 / 2


def test_meeting_without_action_items_penalises_false_positives():
    result = aggregate_extraction([score_extraction([{"text": "Send notes", "assignee": None}], [])])

    assert result["precision"] == 0
    assert result["recall"] == 1.0


def test_summary_format_checks():
    good = score_summary({"overview": "Kickoff.", "key_points": ["A", "B"], "decisions": "Ship Friday."})
    bad = score_summary({"overview": "**Kickoff**", "key_points": ["A"], "decisions": ""})

    assert all(good.values())
    assert bad == {"under_100_words": True, "two_to_three_points": False, "no_markdown": False, "has_decisions": False}


def test_email_checks_item_and_owner_coverage():
    items = [
        {"assignee": "Tom", "keywords": ["duplicate"]},
        {"assignee": "Grace", "keywords": ["acme"]},
    ]
    email = {"body": "Hi team,\n- Investigate the duplicate invoice (Owner: Tom)\nBest regards"}

    result = score_email(email, items)

    assert result["item_coverage"] == 0.5
    assert result["owner_coverage"] == 0.5
    assert result["no_markdown"] and result["under_250_words"]


def test_dataset_is_well_formed():
    samples = json.loads(DATASET.read_text(encoding="utf-8"))

    assert len({s["id"] for s in samples}) == len(samples)
    for sample in samples:
        transcript = "\n".join(sample["transcript"]).lower()
        for item in sample["action_items"]:
            assert item["keywords"], sample["id"]
            for keyword in item["keywords"]:
                assert keyword.lower() in transcript, (sample["id"], keyword)
            if item["assignee"]:
                assert item["assignee"].lower() in transcript, (sample["id"], item["assignee"])
