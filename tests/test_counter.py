"""The live counter keeps customers apart and holds shared notes until approval."""

from __future__ import annotations

from fastapi.testclient import TestClient

from citydesk.api import app
from citydesk.corpus import all_notes, search_notes
from citydesk.service import approve_candidate, record_feedback, reset_desk, resume_turn, take_turn


def _blob(payload: dict) -> str:
    return " ".join(
        message["content"] if isinstance(message["content"], str) else "" for message in payload["messages"]
    )


def test_handbook_finds_the_return_window():
    hits = search_notes("How long is the return window?", k=1)
    assert hits
    assert "30" in hits[0]["text"]
    assert "return" in hits[0]["text"].lower()


def test_counter_keeps_customers_apart():
    reset_desk()
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["shop"] == "lumen"

    remembered = take_turn("chat-1", "Remember that I wear size 42.", "sara")
    assert any("size 42" in fact for fact in remembered["profile"]["facts"])

    again = take_turn("chat-2", "What size do I wear?", "sara")
    assert "size 42" in _blob(again)
    assert again["interrupt"] is None

    sara = take_turn("chat-1", "Can I return my shoes?", "sara")
    assert "L-1042" in _blob(sara)
    assert "still open" in _blob(sara)

    omar = take_turn("chat-3", "Can I return my shoes?", "omar")
    omar_blob = _blob(omar)
    assert "L-0988" in omar_blob
    assert "closed" in omar_blob
    assert "L-1042" not in omar_blob
    assert "size 42" not in omar_blob

    paused = take_turn("chat-1", "Request a refund for my trail shoes.", "sara")
    assert paused["interrupt"]["value"]["action_requests"][0]["name"] == "request_refund"
    resumed = resume_turn(
        "chat-1",
        [{"type": "edit", "edited_action": {"name": "request_refund", "args": {"reason": "Unworn, receipt in the bag"}}}],
        "sara",
    )
    assert resumed["interrupt"] is None
    assert any(entry["reason"] == "Unworn, receipt in the bag" for entry in resumed["refunds"])

    stolen = client.post(
        "/api/desk/turn",
        json={"thread_id": "chat-1", "message": "What size do I wear?", "customer_id": "omar"},
    )
    assert stolen.status_code == 400


def test_feedback_stays_personal_until_someone_approves_it():
    reset_desk()
    turn = take_turn("chat-9", "How long is the return window?", "sara")
    personal = record_feedback(
        "chat-9",
        "sara",
        turn["response_id"],
        "personal",
        2,
        "I prefer shorter answers",
        "Use 14 days for my own gifts.",
        False,
    )
    assert any("14 days" in item["value"] for item in personal["profile"]["corrections"])
    assert personal["candidates"] == []
    assert all("14 days" not in note["body"] for note in all_notes())

    shared = record_feedback(
        "chat-9",
        "sara",
        turn["response_id"],
        "shared",
        1,
        None,
        "Gift cards are non-returnable.",
        True,
    )
    pending = shared["candidates"][-1]
    assert pending["status"] == "pending"
    assert pending["consent_for_training"] is True
    assert all("non-returnable" not in note["body"] for note in all_notes())

    approve_candidate(pending["id"])
    hits = search_notes("Are gift cards returnable?", k=3)
    assert any("non-returnable" in hit["text"] for hit in hits)

    omar = take_turn("chat-8", "What do you remember about me?", "omar")
    assert "14 days" not in _blob(omar)
    assert "size 42" not in _blob(omar)


def test_a_missing_contact_is_feedback_for_every_customer():
    reset_desk()
    turn = take_turn("chat-ap", "Who approves my refund?", "sara")
    before = list(turn["profile"]["facts"])
    saved = record_feedback(
        "chat-ap",
        "sara",
        turn["response_id"],
        "shared",
        1,
        "You did not give the title or email of the approver.",
        "I'm sorry—I still can't verify the approver's title, name, or email.",
        False,
    )
    assert saved["feedback"][-1]["scope"] == "shared"
    assert saved["profile"]["facts"] == before
    assert saved["candidates"][-1]["text"] == "You did not give the title or email of the approver."
    assert "sorry" not in saved["candidates"][-1]["text"].lower()


def test_the_agent_collects_feedback_in_the_chat():
    reset_desk()
    take_turn("chat-fb", "How long is the return window?", "sara")
    asked = take_turn("chat-fb", "That reply was wrong.", "sara")
    assert "rating from 1 to 5" in _blob(asked)
    assert asked["feedback"] == []

    saved = take_turn(
        "chat-fb",
        "Rating 2, personal, the right answer is use 14 days for my gifts.",
        "sara",
    )
    assert any("14 days" in item["value"] for item in saved["profile"]["corrections"])
    assert saved["feedback"][-1]["scope"] == "personal"
    assert saved["feedback"][-1]["rating"] == 2
    assert saved["feedback"][-1]["consent_for_training"] is False
    example = saved["feedback"][-1]["example"]
    assert "14 days" in example["feedback_message"]
    assert "return window" in example["question"].lower()
    assert example["judged_reply"]
    assert "14 days" in example["preferred_reply"]
    assert saved["candidates"] == []

    take_turn("chat-fb2", "How long is the return window?", "sara")
    shared = take_turn(
        "chat-fb2",
        "Rating 1, shared, the right answer is gift cards are non-returnable, keep this example.",
        "sara",
    )
    assert shared["candidates"][-1]["status"] == "pending"
    assert shared["candidates"][-1]["consent_for_training"] is True
    assert all("non-returnable" not in note["body"] for note in all_notes())
