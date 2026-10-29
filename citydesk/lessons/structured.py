"""Station 04 — ToolStrategy ends the loop with a validated object."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from citydesk.lessons.support import RUN, pack
from citydesk.model import DeskChatModel
from citydesk.schemas import BriefCard
from citydesk.tools import search_archive
from citydesk.tracing import trace_scope

META = {
    "id": "structured",
    "number": "04",
    "title": "Structured output",
    "kicker": "A Pydantic model, returned as structured_response",
    "summary": (
        "ToolStrategy adds a hidden tool whose arguments are your schema. With a "
        "provider that implements native structured output you can use ProviderStrategy "
        "instead. ToolStrategy works for any model that can call tools, including the "
        "local one. When the model calls the schema tool, the agent stops and puts a "
        "validated BriefCard on structured_response. Prompted-output parsing is the old path."
    ),
    "look_for": [
        "The tool list includes search_archive and BriefCard. You only passed one real tool.",
        "tool_choice is any while a schema is outstanding, so the model must call a tool.",
        "The card is a validated object: confidence is a float, sources is a list.",
    ],
    "default_prompt": "Brief me on the harbor dredging.",
    "accepts_prompt": True,
    "source": "citydesk/lessons/structured.py",
}


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    agent = create_agent(
        model=DeskChatModel(),
        tools=[search_archive],
        system_prompt="Search the archive, then return a BriefCard. Do not invent dates.",
        response_format=ToolStrategy(BriefCard),
    )
    with trace_scope() as events:
        result = agent.invoke({"messages": [{"role": "user", "content": text}]}, RUN)
    card = result["structured_response"]
    section = pack(
        result,
        events,
        label="structured_response",
        body="The prose is gone. The handler reads the card, not the last message.",
    )
    return {
        "headline": card.headline,
        "sections": [section],
    }
