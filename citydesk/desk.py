"""The shift itself: retrieval, memory, review, and middleware in one agent."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, ModelRequest, PIIMiddleware, dynamic_prompt
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from citydesk.middleware import TraceMiddleware
from citydesk.model import resolve_model
from citydesk.schemas import DeskContext
from citydesk.tools import file_brief, recall_preferences, save_preference, search_archive, who_is_on_duty
from citydesk.tracing import emit


@dynamic_prompt
def desk_prompt(request: ModelRequest) -> str:
    context = request.runtime.context
    reporter = getattr(context, "reporter", "the reporter")
    desk = getattr(context, "desk", "city")
    preference = ""
    store = request.runtime.store
    if store is not None and context is not None:
        item = store.get((reporter,), "notes")
        if item is not None and item.value.get("notes"):
            preference = " Preferences already on file: " + "; ".join(item.value["notes"])
    emit("dynamic_prompt", f"{reporter} on the {desk} desk.{preference}")
    return (
        f"You are the assistant on the {desk} desk at The City Desk, sitting with {reporter}. "
        "Check the archive before you state a fact about Marsa. "
        "File a brief only when the reporter asks you to."
        f"{preference}"
    )


def build_desk():
    """Compile the desk agent. The saver and the store live as long as this object does."""

    model, label = resolve_model()
    agent = create_agent(
        model=model,
        tools=[search_archive, save_preference, recall_preferences, who_is_on_duty, file_brief],
        system_prompt="You work the city desk.",
        middleware=[
            PIIMiddleware("email", strategy="redact", apply_to_input=True),
            PIIMiddleware("press_card", detector=r"PC-\d{4}", strategy="mask", apply_to_input=True),
            desk_prompt,
            TraceMiddleware(),
            HumanInTheLoopMiddleware(interrupt_on={"file_brief": True}),
        ],
        context_schema=DeskContext,
        checkpointer=InMemorySaver(),
        store=InMemoryStore(),
    )
    return agent, label
