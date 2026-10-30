"""The monthly review sorts unused consented feedback and does not repeat it."""

from __future__ import annotations

from citydesk.feedback import build_example
from citydesk.service import record_feedback, reset_desk, take_turn
from citydesk.suggest import build_suggestions


def test_feedback_example_keeps_the_customer_words():
    example = build_example(
        [
            {"type": "human", "content": "How long is the return window?"},
            {"type": "ai", "content": "The return window is 14 days."},
            {"type": "human", "content": "That reply was wrong."},
            {"type": "ai", "content": "I still need a rating from 1 to 5."},
            {"type": "human", "content": "Rating 1, shared, the right answer is gift cards are non-returnable."},
        ],
        "The reply said 14 days.",
        "Gift cards are non-returnable.",
    )
    assert example["question"] == "How long is the return window?"
    assert example["judged_reply"] == "The return window is 14 days."
    assert "That reply was wrong." in example["feedback_message"]
    assert "gift cards" in example["feedback_message"]
    assert example["problem"] == "The reply said 14 days."
    assert example["preferred_reply"] == "Gift cards are non-returnable."


def test_monthly_review_sorts_unused_consent():
    reset_desk()
    turn = take_turn("chat-rev", "How long is the return window?", "sara")
    response_id = turn["response_id"]

    def keep(scope: str, text: str, consent: bool = True) -> None:
        record_feedback("chat-rev", "sara", response_id, scope, 2, None, text, consent)

    keep("shared", "Gift cards are non-returnable.")
    keep("personal", "Use 14 days for my gifts.")
    keep("shared", "The return window is 30 days after delivery.")
    keep("shared", "Please change the delivery address.")
    keep("shared", "A secret shop rule.", False)

    report = build_suggestions()
    by_where = {item["where"]: item for item in report["suggestions"]}

    assert report["reviewed"] == 4
    assert "gift cards" in by_where["handbook"]["what"].lower()
    assert "handbook" in by_where["prompt"]["what"].lower()
    assert "address" in by_where["tool"]["what"].lower()
    assert by_where["ignore"]["where"] == "ignore"
    assert build_suggestions()["reviewed"] == 0
