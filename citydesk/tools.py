"""Tools the desk model is allowed to call.

``ToolRuntime`` carries the reporter, the store, and the call id. Those values
never appear in the arguments the model fills in.
"""

from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from citydesk.corpus import search_notes
from citydesk.schemas import DeskContext
from citydesk.tracing import emit

SPIKE: list[dict[str, str]] = []


@tool
def search_archive(query: str) -> str:
    """Search the Marsa city archive and return the closest notes."""

    hits = search_notes(query, k=2)
    emit("tool:search_archive", query[:120])
    if not hits:
        return "The archive has no note for that."
    blocks = [f"[{hit['title']} · similarity {hit['score']}] {hit['text']}" for hit in hits]
    return "\n\n".join(blocks)


@tool
def save_preference(note: str, runtime: ToolRuntime[DeskContext]) -> str:
    """Remember a reporter preference so a later shift can recall it."""

    reporter = runtime.context.reporter
    if runtime.store is None:
        return "No long-term store is attached to this shift."
    current = runtime.store.get((reporter,), "notes")
    notes = list(current.value.get("notes", [])) if current else []
    if note not in notes:
        notes.append(note)
    runtime.store.put((reporter,), "notes", {"notes": notes})
    emit("tool:save_preference", f"{reporter}: {note[:80]}")
    return f"Saved for later shifts under {reporter}: {note}"


@tool
def recall_preferences(runtime: ToolRuntime[DeskContext]) -> str:
    """Read preferences saved for this reporter across shifts."""

    reporter = runtime.context.reporter
    if runtime.store is None:
        return "No long-term store is attached to this shift."
    current = runtime.store.get((reporter,), "notes")
    notes = list(current.value.get("notes", [])) if current else []
    emit("tool:recall_preferences", reporter)
    if not notes:
        return f"Nothing saved yet for {reporter}."
    return f"On file for {reporter}: " + " | ".join(notes)


@tool
def who_is_on_duty(runtime: ToolRuntime[DeskContext]) -> str:
    """Say which reporter and which desk this shift belongs to."""

    emit("tool:who_is_on_duty", runtime.context.reporter)
    return f"{runtime.context.reporter} is on the {runtime.context.desk} desk."


@tool
def file_brief(headline: str, summary: str) -> str:
    """File a brief on the spike. An editor must approve this before it runs."""

    entry = {"id": f"brief-{len(SPIKE) + 1}", "headline": headline, "summary": summary}
    SPIKE.append(entry)
    emit("tool:file_brief", entry["id"])
    return f"On the spike as {entry['id']}: {headline}"


def clear_spike() -> None:
    SPIKE.clear()
