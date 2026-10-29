"""Turn LangChain messages into JSON the newsroom UI can render."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage


def message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
    return "".join(parts)


def dump_message(message: BaseMessage) -> dict[str, Any]:
    content = message.content
    if not isinstance(content, (str, list, dict)):
        content = str(content)
    data: dict[str, Any] = {"type": message.type, "content": content}
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        data["tool_calls"] = [
            {"name": call.get("name"), "args": call.get("args"), "id": call.get("id")}
            for call in tool_calls
        ]
    tool_call_id = getattr(message, "tool_call_id", None)
    if tool_call_id:
        data["tool_call_id"] = tool_call_id
    status = getattr(message, "status", None)
    if status:
        data["status"] = status
    name = getattr(message, "name", None)
    if name:
        data["name"] = name
    blocks = getattr(message, "content_blocks", None)
    if blocks:
        data["content_blocks"] = _jsonable(blocks)
    return data


def dump_interrupt(result: dict[str, Any]) -> dict[str, Any] | None:
    raw = result.get("__interrupt__") or []
    if not raw:
        return None
    first = raw[0]
    return {"id": first.id, "value": first.value}


def dump_structured(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return _jsonable(value)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)
