"""Station 02 — one chat-model interface, stream and batch included."""

from __future__ import annotations

from langchain.messages import HumanMessage

from citydesk.model import DeskChatModel, resolve_model
from citydesk.serialize import dump_message

META = {
    "id": "models",
    "number": "02",
    "title": "Models",
    "kicker": "invoke, stream, batch — then swap the class",
    "summary": (
        "LangChain talks to providers through BaseChatModel. init_chat_model(\"openai:...\") "
        "returns one. This desk ships DeskChatModel, a local class with the same methods, "
        "so every station runs without a key. Streaming yields message chunks. Batch runs "
        "two prompts through the same model."
    ),
    "look_for": [
        "stream() yields chunks. The tokens below are those chunks, joined only in the headline.",
        "batch() is the same model, many inputs. Agents are not required for either call.",
        "resolve_model() is the seam. Set CITYDESK_MODEL and the desk uses init_chat_model.",
    ],
    "default_prompt": "hello",
    "accepts_prompt": True,
    "source": "citydesk/lessons/models.py",
}


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    model = DeskChatModel()
    _live, label = resolve_model()
    tokens: list[str] = []
    for chunk in model.stream([HumanMessage(text)]):
        tokens.append(str(chunk.content))
    other = "When does the museum reopen?" if text.lower().strip(".!?") == "hello" else "hello"
    batched = model.batch([[HumanMessage(text)], [HumanMessage(other)]])
    return {
        "headline": "".join(tokens),
        "sections": [
            {
                "label": "stream()",
                "body": (
                    f"Active resolver: {label}. The chunks below came from DeskChatModel.stream, "
                    "which is the method a provider model implements too."
                ),
                "messages": [dump_message(message) for message in batched],
                "trace": [],
                "tokens": tokens,
            }
        ],
    }
