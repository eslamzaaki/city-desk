"""A local chat model with the same interface as a provider model.

Stations call this the way they would call ``init_chat_model("openai:...")``.
It reads the turn and returns a tool call or a final sentence, so the agent
loop, the middleware, and the graph all run with no API key.

Swap it for a live model by setting ``CITYDESK_MODEL``. The rest of the desk
does not change.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import PrivateAttr

from citydesk.feedback import feedback_ask, feedback_ready, parse_feedback
from citydesk.serialize import message_text

KNOWN_TOOLS = {
    "search_handbook",
    "lookup_order",
    "save_preference",
    "recall_preferences",
    "request_refund",
    "who_is_shopping",
    "save_feedback",
    "unstable_wire",
    "flaky_wire",
    "write_todos",
}


class DeskChatModel(BaseChatModel):
    """Scripted stand-in for ``init_chat_model``.

    ``fail`` raises, so fallback middleware has a broken model to replace.
    ``loop_tool`` calls that tool forever, so a call budget can stop the loop.
    ``force_tool`` calls that tool once in the turn, then answers.
    """

    fail: bool = False
    loop_tool: str | None = None
    force_tool: str | None = None
    _seq: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "citydesk"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        formatted = [convert_to_openai_tool(tool) for tool in tools]
        return self.bind(desk_tools=formatted, desk_tool_choice=tool_choice)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.fail:
            raise RuntimeError("primary model refused the call")
        message = self._decide(
            messages,
            kwargs.get("desk_tools") or [],
            kwargs.get("desk_tool_choice"),
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        message = self._decide(
            messages,
            kwargs.get("desk_tools") or [],
            kwargs.get("desk_tool_choice"),
        )
        if message.tool_calls:
            yield ChatGenerationChunk(
                message=AIMessageChunk(content="", tool_calls=message.tool_calls)
            )
            return
        words = str(message.content).split(" ")
        for index, word in enumerate(words):
            piece = word if index == 0 else f" {word}"
            yield ChatGenerationChunk(message=AIMessageChunk(content=piece))

    def _decide(self, messages: list[BaseMessage], tools: list[dict], tool_choice: Any) -> AIMessage:
        blob = "\n".join(message_text(message) for message in messages)
        if "Context Extraction Assistant" in blob or "<primary_objective>" in blob:
            excerpt = blob.split("Messages to summarize:", 1)[-1]
            excerpt = excerpt.split("</messages>", 1)[0]
            cleaned = re.sub(r"<[^>]+>", " ", excerpt)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            summary = cleaned[:420] or "Earlier notes from the counter."
            return AIMessage(content=f"Summary: {summary}")

        names = [_tool_name(tool) for tool in tools]
        schemas = dict(zip(names, tools, strict=True))
        human, recent = _split_turn(messages)
        called = _called_names(recent)
        evidence = _evidence(recent)
        must_call = tool_choice == "any"
        forced = _choice_name(tool_choice)

        if self.loop_tool and self.loop_tool in schemas:
            return self._call(self.loop_tool, schemas[self.loop_tool], human, evidence)
        if forced and forced in schemas and forced not in called:
            return self._call(forced, schemas[forced], human, evidence)
        if self.force_tool and self.force_tool in schemas and self.force_tool not in called:
            return self._call(self.force_tool, schemas[self.force_tool], human, evidence)

        schema_tools = [name for name in names if name not in KNOWN_TOOLS]
        if not evidence:
            choice = _first_tool(names, human, schema_tools)
            if choice:
                return self._call(choice, schemas[choice], human, evidence)
            if must_call and schema_tools:
                return self._call(schema_tools[0], schemas[schema_tools[0]], human, evidence)
            if must_call and names:
                return self._call(names[0], schemas[names[0]], human, evidence)
            return AIMessage(content=_plain_reply(human))

        if (
            _wants_order(human)
            and "search_handbook" in schemas
            and "search_handbook" not in called
            and "lookup_order" in called
        ):
            return self._call("search_handbook", schemas["search_handbook"], human, evidence)
        if _wants_refund(human) and "request_refund" in schemas and "request_refund" not in called:
            return self._call("request_refund", schemas["request_refund"], human, evidence)
        pending_schema = [name for name in schema_tools if name not in called]
        if pending_schema:
            return self._call(pending_schema[0], schemas[pending_schema[0]], human, evidence)
        if must_call and names:
            pending = [name for name in names if name not in called] or names
            return self._call(pending[0], schemas[pending[0]], human, evidence)
        return AIMessage(content=_answer(evidence))

    def _call(self, name: str, schema: dict, human: str, evidence: str) -> AIMessage:
        self._seq += 1
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": name,
                    "args": _args_for(schema, human, evidence),
                    "id": f"call_{self._seq}",
                    "type": "tool_call",
                }
            ],
        )


_PROVIDER_DEFAULTS = {
    "openai": "openai:gpt-6.1-sol",
    "anthropic": "anthropic:claude-sonnet-4-5",
}


def resolve_model() -> tuple[BaseChatModel, str]:
    """Pick the counter model from ``CITYDESK_PROVIDER``.

    ``local`` is the scripted desk model. ``openai`` and ``anthropic`` call that
    provider. ``CITYDESK_MODEL`` can name the exact model; otherwise a default
    for the provider is used. An empty provider with an empty model stays local.
    """

    provider = os.getenv("CITYDESK_PROVIDER", "").strip().lower()
    model_name = os.getenv("CITYDESK_MODEL", "").strip()
    if provider in {"", "local"} and not model_name:
        return _local("local DeskChatModel")
    if provider == "local":
        return _local("local DeskChatModel")
    if provider in _PROVIDER_DEFAULTS:
        return _provider(_spec_for(provider, model_name))
    if provider:
        return _local(f"fell back to DeskChatModel (unknown CITYDESK_PROVIDER {provider})")
    return _provider(model_name)


def _spec_for(provider: str, model_name: str) -> str:
    if not model_name or ":" in model_name and not model_name.startswith(f"{provider}:"):
        return _PROVIDER_DEFAULTS[provider]
    if model_name.startswith(f"{provider}:"):
        return model_name
    return f"{provider}:{model_name}"


def _local(label: str) -> tuple[BaseChatModel, str]:
    return DeskChatModel(), label


def _provider(spec: str) -> tuple[BaseChatModel, str]:
    try:
        return init_chat_model(spec), spec
    except Exception as exc:  # a missing provider package should not take the desk down
        return DeskChatModel(), f"fell back to DeskChatModel ({exc.__class__.__name__}: {exc})"


def _tool_name(tool: dict) -> str:
    function = tool.get("function", tool)
    return str(function.get("name", ""))


def _choice_name(choice: Any) -> str | None:
    if choice is None or choice in {"auto", "any", "none", "required"}:
        return None
    if isinstance(choice, str):
        return choice
    if isinstance(choice, dict):
        function = choice.get("function") or {}
        return function.get("name")
    return None


def _split_turn(messages: list[BaseMessage]) -> tuple[str, list[BaseMessage]]:
    last = 0
    human = ""
    for index, message in enumerate(messages):
        if message.type != "human":
            continue
        text = message_text(message)
        if "Context Extraction Assistant" in text or "<primary_objective>" in text:
            continue
        last = index
        human = text
    return human, list(messages[last + 1 :])


def _called_names(messages: list[BaseMessage]) -> set[str]:
    names: set[str] = set()
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            names.add(call["name"])
    return names


def _evidence(messages: list[BaseMessage]) -> str:
    chunks = [message_text(message) for message in messages if message.type == "tool"]
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _is_greeting(text: str) -> bool:
    stripped = text.lower().strip().strip(".!?")
    if stripped in {"hi", "hello", "hey", "thanks", "thank you", "good morning", "good evening"}:
        return True
    return stripped.startswith(("hello", "hi ", "hey ", "thanks"))


def _wants_memory(text: str) -> bool:
    lowered = text.lower().strip()
    if _wants_recall(text):
        return False
    return (
        lowered.startswith("remember")
        or "remember that" in lowered
        or lowered.startswith("i prefer")
        or lowered.startswith("i wear")
        or lowered.startswith("call me")
        or lowered.startswith("correction")
    )


def _wants_recall(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "what do you remember",
            "what size",
            "my size",
            "my preferences",
            "what did i tell you",
            "do you remember",
            "about me",
        )
    )


def _wants_identity(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in ("who am i", "who is shopping", "who's shopping"))


def _wants_order(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in ("my order", "my shoes", "return", "refund", "exchange"))


def _wants_refund(text: str) -> bool:
    return "refund" in text.lower()


def _wants_feedback(text: str) -> bool:
    lowered = text.lower()
    if any(phrase in lowered for phrase in ("feedback", "that was wrong", "that reply", "that answer", "rate this", "rating")):
        return True
    return "the right answer is" in lowered and any(word in lowered for word in ("personal", "shared", "rating"))


def _first_tool(names: list[str], human: str, schema_tools: list[str]) -> str | None:
    if _wants_feedback(human):
        if feedback_ready(parse_feedback(human)) and "save_feedback" in names:
            return "save_feedback"
        return None
    if _wants_recall(human) and "recall_preferences" in names:
        return "recall_preferences"
    if _wants_memory(human) and "save_preference" in names:
        return "save_preference"
    if _wants_identity(human) and "who_is_shopping" in names:
        return "who_is_shopping"
    if _wants_order(human) and "lookup_order" in names:
        return "lookup_order"
    if "write_todos" in names and "plan" in human.lower():
        return "write_todos"
    if (
        "search_handbook" in names
        and not _is_greeting(human)
        and not _wants_memory(human)
        and not _wants_recall(human)
        and not _wants_identity(human)
        and not _wants_feedback(human)
    ):
        return "search_handbook"
    if schema_tools and not _is_greeting(human):
        return schema_tools[0]
    return None


def _plain_reply(human: str) -> str:
    if _wants_feedback(human):
        return feedback_ask(parse_feedback(human))
    if _is_greeting(human):
        return "The counter is open. Ask about a return, an order, shipping, or a product."
    if not human.strip():
        return "Send a question and I will check the handbook before I answer."
    return "I don't have a note on that yet. Ask me to search the handbook."


def _answer(evidence: str) -> str:
    if evidence:
        return f"{evidence.strip()}\n\nAnswered from the handbook and this customer's own record."
    return "I don't have a note on that yet. Ask me to search the handbook."


def _headline(text: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s", text.strip())[0]
    cleaned = re.sub(r"^\[[^\]]+\]\s*", "", sentence)
    return (cleaned[:120] or "Lumen counter").strip()


def _args_for(schema: dict, human: str, evidence: str) -> dict[str, Any]:
    function = schema.get("function", schema)
    params = (function.get("parameters") or {}).get("properties") or {}
    source = evidence or human
    if "rating" in params and "scope" in params and "corrected_answer" in params:
        parsed = parse_feedback(human)
        return {
            "rating": parsed["rating"] or 1,
            "scope": parsed["scope"] or "personal",
            "reason": parsed["reason"],
            "corrected_answer": parsed["corrected_answer"],
            "consent_for_training": bool(parsed["consent_for_training"]),
        }
    args: dict[str, Any] = {}
    for key in params:
        if key in {"query", "topic", "note", "question"}:
            args[key] = human[:240]
        elif key == "reason":
            args[key] = (human or source)[:300]
        elif key == "headline":
            args[key] = _headline(source)
        elif key == "summary":
            args[key] = source[:500]
        elif key == "confidence":
            args[key] = 0.74 if evidence else 0.4
        elif key == "sources":
            args[key] = ["shop-handbook"] if evidence else []
        elif key == "todos":
            args[key] = [
                {"content": "Check the return policy", "status": "completed"},
                {"content": "Answer in this customer's style", "status": "in_progress"},
            ]
    return args
