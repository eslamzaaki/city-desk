"""Small helpers so a lesson file can stay about the LangChain call."""

from __future__ import annotations

from typing import Any

from citydesk.serialize import dump_interrupt, dump_message, dump_structured

RUN = {"recursion_limit": 20}


def pack(
    result: dict[str, Any],
    events: list[dict[str, str]] | None = None,
    *,
    label: str,
    body: str,
    **extra: Any,
) -> dict[str, Any]:
    section: dict[str, Any] = {
        "label": label,
        "body": body,
        "messages": [dump_message(message) for message in result.get("messages", [])],
        "trace": list(events or []),
    }
    structured = dump_structured(result.get("structured_response"))
    if structured is not None:
        section["card"] = structured
    if result.get("todos") is not None:
        section["todos"] = result["todos"]
    interrupt = dump_interrupt(result)
    if interrupt is not None:
        section["interrupt"] = interrupt
    section.update(extra)
    return section
