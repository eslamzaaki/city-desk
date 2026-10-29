"""Middleware that records the agent loop for the wire panel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    wrap_tool_call,
)
from langchain.messages import ToolMessage

from citydesk.tracing import emit


class TraceMiddleware(AgentMiddleware):
    """Write one line each time the agent loop enters a hook."""

    def before_agent(self, state, runtime) -> dict[str, Any] | None:
        emit("before_agent", f"{len(state['messages'])} messages waiting")
        return None

    def before_model(self, state, runtime) -> dict[str, Any] | None:
        emit("before_model", f"about to call the model with {len(state['messages'])} messages")
        return None

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        system = ""
        if request.system_message is not None:
            content = request.system_message.content
            system = content if isinstance(content, str) else str(content)
        tool_names = []
        for tool in request.tools or []:
            name = getattr(tool, "name", None)
            if name:
                tool_names.append(name)
        preview = " ".join(system.split())[:180]
        emit(
            "wrap_model_call",
            f"tools=[{', '.join(tool_names)}] system: {preview}" if preview else f"tools=[{', '.join(tool_names)}]",
        )
        return handler(request)

    def after_model(self, state, runtime) -> dict[str, Any] | None:
        last = state["messages"][-1]
        calls = getattr(last, "tool_calls", None) or []
        if calls:
            emit("after_model", "tool calls: " + ", ".join(call["name"] for call in calls))
        else:
            text = last.content if isinstance(last.content, str) else ""
            emit("after_model", f"final text ({len(text)} chars)")
        return None

    def wrap_tool_call(self, request, handler):
        name = request.tool_call.get("name", "tool")
        emit("wrap_tool_call", f"{name} {request.tool_call.get('args', {})}")
        return handler(request)

    def after_agent(self, state, runtime) -> dict[str, Any] | None:
        emit("after_agent", "shift step finished")
        return None


@wrap_tool_call
def catch_tool_errors(request, handler):
    """``wrap_tool_call`` body: a raised tool becomes a tool message, not a crash."""

    try:
        return handler(request)
    except Exception as exc:
        emit("wrap_tool_call:error", str(exc))
        return ToolMessage(
            content=f"Tool error caught: {exc}",
            tool_call_id=request.tool_call["id"],
            status="error",
        )
