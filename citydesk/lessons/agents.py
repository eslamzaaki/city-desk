"""Station 05 — create_agent is the v1 loop."""

from __future__ import annotations

from langchain.agents import create_agent

from citydesk.lessons.support import RUN, pack
from citydesk.middleware import TraceMiddleware
from citydesk.model import DeskChatModel
from citydesk.tools import search_archive
from citydesk.tracing import trace_scope

META = {
    "id": "agents",
    "number": "05",
    "title": "Agents",
    "kicker": "create_agent replaced create_react_agent",
    "summary": (
        "create_agent compiles a LangGraph that calls the model, runs the tools it "
        "asked for, and repeats until the model stops calling tools. Middleware, "
        "checkpointers, and stores attach here. The prebuilt create_react_agent in "
        "langgraph.prebuilt is the deprecated door. The node that used to be named "
        "agent is named model."
    ),
    "look_for": [
        "The transcript is human → model tool call → tool message → model text.",
        "The trace hooks fire around that loop. They are middleware, not a second framework.",
        "No tool call on the last model turn is what ends it.",
    ],
    "default_prompt": "When does harbor dredging start?",
    "accepts_prompt": True,
    "source": "citydesk/lessons/agents.py",
}


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    agent = create_agent(
        model=DeskChatModel(),
        tools=[search_archive],
        system_prompt="You are the harbor desk. Search before you assert a fact about Marsa.",
        middleware=[TraceMiddleware()],
    )
    with trace_scope() as events:
        result = agent.invoke({"messages": [{"role": "user", "content": text}]}, RUN)
    reply = result["messages"][-1].content
    headline = reply if isinstance(reply, str) else "The agent finished the loop."
    return {
        "headline": headline.split("\n")[0][:180],
        "sections": [
            pack(
                result,
                events,
                label="One loop, then a stop",
                body="Read the trace top to bottom. before_model, the call, the tool, the model again, after_agent.",
            )
        ],
    }
