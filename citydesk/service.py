"""The live counter: one compiled agent, a chat per thread, memory per customer."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.types import Command

from citydesk.corpus import add_handbook_note, all_notes, clear_extra_notes
from citydesk.feedback import is_shop_rule
from citydesk.desk import build_desk
from citydesk.personal import shop_personal
from citydesk.schemas import ShopContext
from citydesk.serialize import dump_interrupt, dump_message
from citydesk.shop import apply_note, ensure_seed, read_profile, require_customer, write_profile
from citydesk.tools import REFUNDS, clear_refunds
from citydesk.tracing import trace_scope

_agent = None
_label = ""
_threads: dict[str, dict[str, str]] = {}
_response_ids: dict[str, set[str]] = {}
_last_response: dict[str, str] = {}
FEEDBACK = shop_personal.feedback
CANDIDATES: list[dict[str, Any]] = []


def reset_desk() -> None:
    global _agent, _label
    _agent = None
    _label = ""
    _threads.clear()
    _response_ids.clear()
    _last_response.clear()
    FEEDBACK.clear()
    CANDIDATES.clear()
    clear_refunds()
    clear_extra_notes()


def _bundle():
    global _agent, _label
    if _agent is None:
        _agent, _label = build_desk()
    return _agent, _label


def list_threads(customer_id: str | None = None) -> list[dict[str, str]]:
    rows = []
    for thread_id, meta in _threads.items():
        if customer_id and meta.get("customer_id") != customer_id:
            continue
        rows.append({"id": thread_id, **meta})
    return rows


def _bind_thread(thread_id: str, customer_id: str, title: str) -> None:
    require_customer(customer_id)
    current = _threads.get(thread_id)
    if current is None:
        _threads[thread_id] = {"title": title[:72], "customer_id": customer_id}
        return
    if current["customer_id"] != customer_id:
        raise ValueError("This chat belongs to another customer.")


def take_turn(thread_id: str, message: str, customer_id: str) -> dict[str, Any]:
    require_customer(customer_id)
    _bind_thread(thread_id, customer_id, message)
    agent, label = _bundle()
    ensure_seed(agent.store, customer_id)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    with trace_scope() as events:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config,
            context=ShopContext(customer_id=customer_id),
        )
    return _payload(thread_id, result, events, customer_id, label, new_response=True)


def resume_turn(thread_id: str, decisions: list[dict], customer_id: str) -> dict[str, Any]:
    require_customer(customer_id)
    if thread_id not in _threads:
        raise KeyError(thread_id)
    _bind_thread(thread_id, customer_id, _threads[thread_id]["title"])
    agent, label = _bundle()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    with trace_scope() as events:
        result = agent.invoke(
            Command(resume={"decisions": sanitize_decisions(decisions)}),
            config,
            context=ShopContext(customer_id=customer_id),
        )
    return _payload(thread_id, result, events, customer_id, label, new_response=True)


def read_thread(thread_id: str, customer_id: str) -> dict[str, Any]:
    require_customer(customer_id)
    agent, label = _bundle()
    ensure_seed(agent.store, customer_id)
    if thread_id not in _threads:
        return _payload(thread_id, {"messages": []}, [], customer_id, label, new_response=False)
    _bind_thread(thread_id, customer_id, _threads[thread_id]["title"])
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = agent.get_state(config)
    values = snapshot.values or {}
    interrupts = list(getattr(snapshot, "interrupts", None) or [])
    result: dict[str, Any] = {"messages": values.get("messages", [])}
    if interrupts:
        result["__interrupt__"] = interrupts
    return _payload(thread_id, result, [], customer_id, label, new_response=False)


def last_response_id(thread_id: str) -> str:
    return _last_response.get(thread_id, "")


def record_feedback(
    thread_id: str,
    customer_id: str,
    response_id: str,
    scope: str,
    rating: int,
    reason: str | None,
    corrected_answer: str | None,
    consent_for_training: bool,
    messages: list | None = None,
) -> dict[str, Any]:
    """Store feedback. Personal notes stay on the customer. Shared notes wait for approval."""

    require_customer(customer_id)
    if scope not in {"personal", "shared"}:
        raise ValueError("Feedback scope must be personal or shared.")
    if thread_id not in _threads:
        raise KeyError(thread_id)
    _bind_thread(thread_id, customer_id, _threads[thread_id]["title"])
    if response_id not in _response_ids.get(thread_id, set()):
        raise ValueError("That reply is not part of this chat.")
    agent, _label = _bundle()
    profile = ensure_seed(agent.store, customer_id)
    if scope == "personal":
        if reason:
            apply_note(profile, reason, thread_id)
        if corrected_answer:
            profile["corrections"].append(
                {
                    "topic": "reply",
                    "value": corrected_answer.strip()[:500],
                    "source_thread": thread_id,
                    "response_id": response_id,
                }
            )
        write_profile(agent.store, customer_id, profile)
    text = (corrected_answer or "").strip()
    if scope == "shared" and not is_shop_rule(text):
        text = (reason or text).strip()
    if scope == "shared" and text:
        CANDIDATES.append(
            {
                "id": f"cand-{len(CANDIDATES) + 1}",
                "customer_id": customer_id,
                "text": text[:500],
                "status": "pending",
                "consent_for_training": consent_for_training,
                "source_thread": thread_id,
                "response_id": response_id,
            }
        )
    shop_personal.record(
        user_id=customer_id,
        thread_id=thread_id,
        response_id=response_id,
        rating=rating,
        scope=scope,
        reason=reason,
        corrected_answer=corrected_answer,
        consent_for_training=consent_for_training,
        messages=messages,
    )
    return read_thread(thread_id, customer_id)


def approve_candidate(candidate_id: str) -> dict[str, Any]:
    """A reviewed shared note enters the handbook. Pending notes are invisible to search."""

    found = next((item for item in CANDIDATES if item["id"] == candidate_id), None)
    if found is None:
        raise KeyError(candidate_id)
    if found["status"] != "pending":
        raise ValueError("That note was already reviewed.")
    found["status"] = "approved"
    add_handbook_note(candidate_id, "Approved correction", found["text"])
    return {"candidate": dict(found), "candidates": [dict(item) for item in CANDIDATES]}


def sanitize_decisions(decisions: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for decision in decisions:
        kind = decision.get("type")
        if kind == "approve":
            cleaned.append({"type": "approve"})
        elif kind == "reject":
            cleaned.append({"type": "reject", "message": str(decision.get("message") or "Hold the refund.")[:300]})
        elif kind == "edit":
            action = decision.get("edited_action") or {}
            args = action.get("args") or {}
            cleaned.append(
                {
                    "type": "edit",
                    "edited_action": {
                        "name": "request_refund",
                        "args": {"reason": str(args.get("reason") or "Customer asked for a refund")[:300]},
                    },
                }
            )
        elif kind == "respond":
            cleaned.append({"type": "respond", "message": str(decision.get("message") or "")[:500]})
        else:
            raise ValueError(f"Unknown decision: {kind}")
    if not cleaned:
        raise ValueError("A decision is required.")
    return cleaned


def _payload(thread_id, result, events, customer_id, label, *, new_response: bool) -> dict[str, Any]:
    agent, _label = _bundle()
    if new_response:
        response_id = uuid4().hex[:12]
        _response_ids.setdefault(thread_id, set()).add(response_id)
        _last_response[thread_id] = response_id
    else:
        response_id = _last_response.get(thread_id, "")
    return {
        "thread_id": thread_id,
        "response_id": response_id,
        "model": label,
        "messages": [dump_message(message) for message in result.get("messages", [])],
        "interrupt": dump_interrupt(result),
        "trace": list(events),
        "profile": read_profile(agent.store, customer_id),
        "refunds": [dict(entry) for entry in REFUNDS if entry["customer_id"] == customer_id],
        "feedback": [dict(item) for item in FEEDBACK if item["customer_id"] == customer_id],
        "candidates": [dict(item) for item in CANDIDATES],
        "handbook": [{"id": note["id"], "title": note["title"]} for note in all_notes()],
        "customer_id": customer_id,
        "threads": list_threads(customer_id),
    }
