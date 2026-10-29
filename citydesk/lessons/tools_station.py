"""Station 03 — @tool schemas, plus ToolRuntime for values the model must not invent."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.utils.function_calling import convert_to_openai_tool

from citydesk.model import DeskChatModel
from citydesk.schemas import DeskContext
from citydesk.lessons.support import RUN, pack
from citydesk.tools import search_archive
from citydesk.tracing import emit, trace_scope

META = {
    "id": "tools",
    "number": "03",
    "title": "Tools",
    "kicker": "A schema for the model, a runtime for the app",
    "summary": (
        "@tool turns a function into a tool the model can call. The JSON schema is "
        "what the model sees. ToolRuntime injects the reporter, the store, and the "
        "call id when the tool actually runs. Those fields stay out of the schema, "
        "so the model cannot invent a reporter name and have the tool trust it."
    ),
    "look_for": [
        "The schema under the wire has query. It does not have reporter.",
        "who_is_on_duty reads runtime.context. The model called it with empty args.",
        "search_archive.invoke runs the tool with no model at all. Tools are ordinary functions.",
    ],
    "default_prompt": "Who is on duty on the harbor desk?",
    "accepts_prompt": True,
    "source": "citydesk/lessons/tools_station.py",
}


@tool
def who_is_on_duty(runtime: ToolRuntime[DeskContext]) -> str:
    """Say which reporter and which desk this shift belongs to."""

    emit("tool:who_is_on_duty", runtime.context.reporter)
    return f"{runtime.context.reporter} is on the {runtime.context.desk} desk."


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    direct = search_archive.invoke({"query": "corniche flood"})
    schema = convert_to_openai_tool(who_is_on_duty)
    agent = create_agent(
        model=DeskChatModel(),
        tools=[who_is_on_duty, search_archive],
        system_prompt="You are the harbor desk. Use tools instead of guessing.",
        context_schema=DeskContext,
    )
    with trace_scope() as events:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": text}]},
            RUN,
            context=DeskContext(reporter="Nour El-Sayed", desk="harbor"),
        )
    section = pack(
        result,
        events,
        label="The agent calls, the runtime fills in the reporter",
        body=(
            "Direct call, no model: "
            + direct.split("\n\n")[0][:180]
            + ". The schema the model was shown is in the extra block."
        ),
        schema=schema,
    )
    return {
        "headline": "The model chooses the tool. The app supplies the reporter.",
        "sections": [section],
    }
