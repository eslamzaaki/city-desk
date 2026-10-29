"""The live shift: one compiled agent, many threads, one store."""

from __future__ import annotations

from typing import Any

from langgraph.types import Command

from citydesk.desk import build_desk
from citydesk.schemas import DeskContext
from citydesk.serialize import dump_interrupt, dump_message
from citydesk.tools import SPIKE, clear_spike
from citydesk.tracing import trace_scope

_agent = None
_label = ""
_threads: dict[str, dict[str, str]] = {}


def reset_desk() -> None:
    global _agent, _label
    _agent = None
    _label = ""
    _threads.clear()
    clear_spike()


def _bundle():
    global _agent, _label
    if _agent is None:
        _agent, _label = build_desk()
    return _agent, _label


def list_threads() -> list[dict[str, str]]:
    return [{"id": thread_id, **meta} for thread_id, meta in _threads.items()]


def take_turn(thread_id: str, message: str, reporter: str, desk: str) -> dict[str, Any]:
    agent, label = _bundle()
    if thread_id not in _threads:
        _threads[thread_id] = {"title": message[:72], "reporter": reporter, "desk": desk}
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
    with trace_scope() as events:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config,
            context=DeskContext(reporter=reporter, desk=desk),
        )
    return _payload(thread_id, result, events, reporter, desk, label)


def resume_turn(thread_id: str, decisions: list[dict], reporter: str, desk: str) -> dict[str, Any]:
    if thread_id not in _threads:
        raise KeyError(thread_id)
    agent, label = _bundle()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
    with trace_scope() as events:
        result = agent.invoke(
            Command(resume={"decisions": sanitize_decisions(decisions)}),
            config,
            context=DeskContext(reporter=reporter, desk=desk),
        )
    return _payload(thread_id, result, events, reporter, desk, label)


def read_thread(thread_id: str, reporter: str, desk: str) -> dict[str, Any]:
    agent, label = _bundle()
    if thread_id not in _threads:
        return _payload(thread_id, {"messages": []}, [], reporter, desk, label)
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = agent.get_state(config)
    values = snapshot.values or {}
    interrupts = list(getattr(snapshot, "interrupts", None) or [])
    result: dict[str, Any] = {"messages": values.get("messages", [])}
    if interrupts:
        result["__interrupt__"] = interrupts
    return _payload(thread_id, result, [], reporter, desk, label)


def sanitize_decisions(decisions: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for decision in decisions:
        kind = decision.get("type")
        if kind == "approve":
            cleaned.append({"type": "approve"})
        elif kind == "reject":
            cleaned.append({"type": "reject", "message": str(decision.get("message") or "Hold the brief.")[:300]})
        elif kind == "edit":
            action = decision.get("edited_action") or {}
            args = action.get("args") or {}
            cleaned.append(
                {
                    "type": "edit",
                    "edited_action": {
                        "name": "file_brief",
                        "args": {
                            "headline": str(args.get("headline") or "Untitled")[:180],
                            "summary": str(args.get("summary") or "")[:800],
                        },
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


def _memories(agent, reporter: str) -> list[str]:
    store = agent.store
    if store is None:
        return []
    item = store.get((reporter,), "notes")
    if item is None:
        return []
    return list(item.value.get("notes", []))


def _payload(thread_id, result, events, reporter, desk, label) -> dict[str, Any]:
    agent, _label = _bundle()
    return {
        "thread_id": thread_id,
        "model": label,
        "messages": [dump_message(message) for message in result.get("messages", [])],
        "interrupt": dump_interrupt(result),
        "trace": list(events),
        "memories": _memories(agent, reporter),
        "spike": [dict(entry) for entry in SPIKE],
        "reporter": reporter,
        "desk": desk,
        "threads": list_threads(),
    }
