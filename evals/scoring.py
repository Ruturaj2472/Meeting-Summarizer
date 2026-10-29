"""Deterministic scoring for the evaluation — no LLM judge, so results are reproducible."""
import re

MARKDOWN = re.compile(r"\*|#|`|__")

def first_name(name):
    return name.strip().split()[0].lower() if name and name.strip() else None

def word_count(text: str) -> int:
    return len(text.split())

def match_items(predicted: list, gold: list) -> list:
    """Greedy one-to-one matching: a predicted item matches a gold item when its
    text contains every one of the gold item's keywords (case-insensitive)."""
    unmatched = list(range(len(predicted)))
    pairs = []
    for gold_item in gold:
        for index in unmatched:
            text = (predicted[index].get("text") or "").lower()
            if all(keyword.lower() in text for keyword in gold_item["keywords"]):
                pairs.append((gold_item, predicted[index]))
                unmatched.remove(index)
                break
    return pairs

def score_extraction(predicted: list, gold: list) -> dict:
    pairs = match_items(predicted, gold)
    return {
        "true_positives": len(pairs),
        "predicted": len(predicted),
        "gold": len(gold),
        "assignee_correct": sum(
            first_name(g["assignee"]) == first_name(p.get("assignee")) for g, p in pairs
        ),
    }

def aggregate_extraction(scores: list) -> dict:
    tp = sum(s["true_positives"] for s in scores)
    predicted = sum(s["predicted"] for s in scores)
    gold = sum(s["gold"] for s in scores)
    precision = tp / predicted if predicted else 1.0
    recall = tp / gold if gold else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "assignee_accuracy": sum(s["assignee_correct"] for s in scores) / tp if tp else 0.0,
    }

def score_summary(summary: dict) -> dict:
    points = summary.get("key_points") or []
    decisions = summary.get("decisions") or ""
    text = " ".join([summary.get("overview") or "", *points, decisions])
    return {
        "under_100_words": word_count(text) <= 100,
        "two_to_three_points": 2 <= len(points) <= 3,
        "no_markdown": not MARKDOWN.search(text),
        "has_decisions": bool(decisions.strip()),
    }

def score_email(email: dict, items: list) -> dict:
    body = email.get("body") or ""
    lower = body.lower()
    assigned = [i for i in items if i.get("assignee")]
    return {
        "item_coverage": sum(
            all(k.lower() in lower for k in i["keywords"]) for i in items
        ) / len(items) if items else 1.0,
        "owner_coverage": sum(
            first_name(i["assignee"]) in lower for i in assigned
        ) / len(assigned) if assigned else 1.0,
        "no_markdown": not MARKDOWN.search(body),
        "under_250_words": word_count(body) <= 250,
    }

def mean(values) -> float:
    values = [float(v) for v in values]
    return sum(values) / len(values) if values else 0.0

def pass_rate(checks: list) -> dict:
    """Average each check across samples (booleans become a 0-1 pass rate)."""
    if not checks:
        return {}
    return {key: mean(c[key] for c in checks) for key in checks[0]}
