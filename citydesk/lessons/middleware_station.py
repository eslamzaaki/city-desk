"""Station 07 — middleware is how you change the loop without forking it."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ModelRequest,
    PIIMiddleware,
    SummarizationMiddleware,
    TodoListMiddleware,
    ToolRetryMiddleware,
    dynamic_prompt,
)

from citydesk.lessons.support import RUN, pack
from citydesk.middleware import TraceMiddleware, catch_tool_errors
from citydesk.model import DeskChatModel
from citydesk.schemas import DeskContext
from citydesk.tools import search_archive
from citydesk.tracing import emit, trace_scope
from langchain.tools import tool

META = {
    "id": "middleware",
    "number": "07",
    "title": "Middleware",
    "kicker": "Hooks around the model and the tools",
    "summary": (
        "Middleware is the v1 replacement for pre_model_hook and post_model_hook. "
        "Node-style hooks (before_model, after_model) update state. Wrap-style hooks "
        "(wrap_model_call, wrap_tool_call) can retry, swap the model, or turn an "
        "exception into a tool message. @dynamic_prompt rewrites the system message "
        "on each call. The built-ins on this station — PII, fallback, call limits, "
        "retries, todos, summarization — are the same hooks with a name."
    ),
    "look_for": [
        "The email is gone before the model runs. The human message in state is already redacted.",
        "A tool that raises does not kill the agent once wrap_tool_call catches it.",
        "The call budget ends the loop while the model still wants another tool call.",
        "Summarization folds older messages into one note. The trigger here is message count, not tokens.",
    ],
    "default_prompt": "",
    "accepts_prompt": False,
    "source": "citydesk/lessons/middleware_station.py",
}

_ATTEMPTS = {"n": 0}


@dynamic_prompt
def harbor_prompt(request: ModelRequest) -> str:
    desk = getattr(request.runtime.context, "desk", "city")
    emit("dynamic_prompt", f"desk={desk}")
    return f"You write for the {desk} desk. Be concrete and use the tools."


@tool
def unstable_wire(topic: str) -> str:
    """A wire that is down."""

    raise RuntimeError("the harbor wire is down")


@tool
def flaky_wire(topic: str) -> str:
    """A wire that fails twice, then answers."""

    _ATTEMPTS["n"] += 1
    emit("tool:flaky_wire", f"attempt {_ATTEMPTS['n']}")
    if _ATTEMPTS["n"] < 3:
        raise RuntimeError(f"down on attempt {_ATTEMPTS['n']}")
    return "Wire restored on the third try."


def run(prompt: str | None = None) -> dict:
    del prompt
    sections = [
        _pii_and_prompt(),
        _caught_error(),
        _retry(),
        _fallback(),
        _budget(),
        _todos(),
        _summary(),
    ]
    return {
        "headline": "Seven ways to stand in the loop without rewriting the agent.",
        "sections": sections,
    }


def _pii_and_prompt() -> dict:
    agent = create_agent(
        model=DeskChatModel(),
        tools=[],
        middleware=[
            PIIMiddleware("email", strategy="redact", apply_to_input=True),
            PIIMiddleware("press_card", detector=r"PC-\d{4}", strategy="mask", apply_to_input=True),
            harbor_prompt,
            TraceMiddleware(),
        ],
        context_schema=DeskContext,
    )
    with trace_scope() as events:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Email nour@marsa.test, press card PC-4412, and confirm the desk is open.",
                    }
                ]
            },
            RUN,
            context=DeskContext(reporter="Nour El-Sayed", desk="harbor"),
        )
    return pack(
        result,
        events,
        label="PII redaction and a dynamic prompt",
        body=(
            "PIIMiddleware rewrote the user message. dynamic_prompt replaced the system "
            "message with the harbor desk line. Both show up in the trace."
        ),
    )


def _caught_error() -> dict:
    agent = create_agent(
        model=DeskChatModel(force_tool="unstable_wire"),
        tools=[unstable_wire],
        middleware=[catch_tool_errors, TraceMiddleware()],
    )
    with trace_scope() as events:
        result = agent.invoke({"messages": [{"role": "user", "content": "Check the harbor wire."}]}, RUN)
    return pack(
        result,
        events,
        label="wrap_tool_call turns a crash into a tool message",
        body="The tool raised. The agent still produced a final message, because the wrapper returned a ToolMessage.",
    )


def _retry() -> dict:
    _ATTEMPTS["n"] = 0
    agent = create_agent(
        model=DeskChatModel(force_tool="flaky_wire"),
        tools=[flaky_wire],
        middleware=[ToolRetryMiddleware(max_retries=3)],
    )
    with trace_scope() as events:
        result = agent.invoke({"messages": [{"role": "user", "content": "Ping the wire."}]}, RUN)
    return pack(
        result,
        events,
        label="ToolRetryMiddleware",
        body=f"The tool ran {_ATTEMPTS['n']} times. The transcript shows the successful result, not the two failures.",
    )


def _fallback() -> dict:
    agent = create_agent(
        model=DeskChatModel(fail=True),
        tools=[],
        middleware=[ModelFallbackMiddleware(DeskChatModel())],
    )
    with trace_scope() as events:
        result = agent.invoke({"messages": [{"role": "user", "content": "hello"}]}, RUN)
    return pack(
        result,
        events,
        label="ModelFallbackMiddleware",
        body="The primary model raises. The fallback model answers. The caller still used create_agent once.",
    )


def _budget() -> dict:
    agent = create_agent(
        model=DeskChatModel(loop_tool="search_archive"),
        tools=[search_archive],
        middleware=[ModelCallLimitMiddleware(run_limit=1, exit_behavior="end")],
    )
    with trace_scope() as events:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "When does harbor dredging start?"}]},
            RUN,
        )
    return pack(
        result,
        events,
        label="ModelCallLimitMiddleware",
        body="run_limit=1. The model would have searched forever. The middleware ends the run and writes the reason.",
    )


def _todos() -> dict:
    agent = create_agent(
        model=DeskChatModel(),
        tools=[],
        middleware=[TodoListMiddleware()],
    )
    with trace_scope() as events:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "Plan the corniche flood coverage."}]},
            RUN,
        )
    return pack(
        result,
        events,
        label="TodoListMiddleware",
        body="The middleware adds a write_todos tool and a todos channel on state. The plan is structured, not a paragraph.",
    )


def _summary() -> dict:
    agent = create_agent(
        model=DeskChatModel(),
        tools=[],
        middleware=[
            SummarizationMiddleware(
                model=DeskChatModel(),
                trigger=("messages", 4),
                keep=("messages", 2),
            )
        ],
    )
    with trace_scope() as events:
        result = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": "Harbor dredging starts Monday at pier 4."},
                    {"role": "user", "content": "The corniche flooded between kilometre 2 and kilometre 4."},
                    {"role": "user", "content": "The tram extension adds a Customs House stop."},
                    {"role": "user", "content": "What should the morning brief lead with?"},
                ]
            },
            RUN,
        )
    return pack(
        result,
        events,
        label="SummarizationMiddleware",
        body="Four messages crossed the trigger. Older turns were compressed. The last question is still in the thread.",
    )
