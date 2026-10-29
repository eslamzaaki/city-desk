"""Station 09 — HumanInTheLoopMiddleware pauses on file_brief."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from citydesk.lessons.support import pack
from citydesk.model import DeskChatModel
from citydesk.tools import clear_spike, file_brief, search_archive
from citydesk.tracing import trace_scope

META = {
    "id": "review",
    "number": "09",
    "title": "Human review",
    "kicker": "An interrupt, then Command(resume=...)",
    "summary": (
        "HumanInTheLoopMiddleware raises a LangGraph interrupt before file_brief runs. "
        "The tool does not run. You resume the same thread with Command(resume=...) and "
        "a decision: approve, edit, reject, or respond. The checkpointer is required, "
        "because the pause has to land somewhere. Search is not gated. Filing is."
    ),
    "look_for": [
        "The paused payload lists action_requests and the decisions you are allowed to return.",
        "Approve runs the tool with the model's arguments.",
        "Edit runs the tool with your arguments. Reject never runs it.",
    ],
    "default_prompt": "File a brief on the corniche flood.",
    "accepts_prompt": True,
    "source": "citydesk/lessons/review.py",
}


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    clear_spike()
    agent = create_agent(
        model=DeskChatModel(),
        tools=[search_archive, file_brief],
        system_prompt="Search, then file a brief only when asked.",
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"file_brief": True})],
        checkpointer=InMemorySaver(),
    )
    approved = _scenario(agent, "approve", text, {"type": "approve"})
    edited = _scenario(
        agent,
        "edit",
        text,
        None,
    )
    rejected = _scenario(
        agent,
        "reject",
        text,
        {"type": "reject", "message": "Hold it. Confirm the kilometre markers first."},
    )
    return {
        "headline": "Nothing reaches the spike until this thread is resumed.",
        "sections": [approved, edited, rejected],
    }


def _scenario(agent, thread_id: str, text: str, decision: dict | None) -> dict:
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
    with trace_scope() as paused_events:
        paused = agent.invoke({"messages": [{"role": "user", "content": text}]}, config)
    if decision is None:
        action = paused["__interrupt__"][0].value["action_requests"][0]
        args = dict(action["args"])
        args["headline"] = "Corniche flood: pumps at noon, upper walk still open"
        decision = {"type": "edit", "edited_action": {"name": "file_brief", "args": args}}
        label = "Edit, then resume"
        body = "The headline on the spike is the editor's sentence, not the model's."
    elif decision["type"] == "approve":
        label = "Approve"
        body = "Same arguments the model proposed. The tool runs after resume."
    else:
        label = "Reject"
        body = "The tool message is the rejection. file_brief never ran."
    with trace_scope() as events:
        resumed = agent.invoke(Command(resume={"decisions": [decision]}), config)
    section = pack(resumed, paused_events + events, label=label, body=body)
    section["interrupt"] = pack(paused, label="paused", body="").get("interrupt")
    return section
