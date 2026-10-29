"""Station 06 — stream_mode='updates' is how a UI watches the loop."""

from __future__ import annotations

from langchain.agents import create_agent

from citydesk.model import DeskChatModel
from citydesk.serialize import message_text
from citydesk.tools import search_archive

META = {
    "id": "streaming",
    "number": "06",
    "title": "Streaming",
    "kicker": "Updates arrive per node, not at the end",
    "summary": (
        "agent.stream(..., stream_mode='updates') yields a dict per node as that node "
        "finishes. In v1 the model node is named model. The tools node follows it. "
        "A chat UI draws from this stream. Token streaming is the model's own stream(); "
        "this station is the graph stream, which is what you want when tools are in the loop."
    ),
    "look_for": [
        "The first chunk is the model node, and it holds a tool call, not the answer.",
        "The tools node carries the archive note.",
        "The second model chunk is the sentence the reader sees.",
    ],
    "default_prompt": "Where did the corniche flood?",
    "accepts_prompt": True,
    "source": "citydesk/lessons/streaming.py",
}


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    agent = create_agent(
        model=DeskChatModel(),
        tools=[search_archive],
        system_prompt="Search the archive, then answer with the note.",
    )
    steps: list[dict[str, str]] = []
    final = ""
    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": text}]},
        {"recursion_limit": 20},
        stream_mode="updates",
    ):
        for node, update in chunk.items():
            messages = update.get("messages") or []
            last = messages[-1] if messages else None
            if last is None:
                summary = node
            else:
                calls = getattr(last, "tool_calls", None) or []
                if calls:
                    summary = "calls " + ", ".join(call["name"] for call in calls)
                else:
                    summary = message_text(last)[:220]
                    if node == "model" and summary:
                        final = summary
            steps.append({"node": node, "summary": summary})
    return {
        "headline": final.split("\n")[0][:180] or "Stream finished.",
        "sections": [
            {
                "label": "stream_mode='updates'",
                "body": "Each row is one chunk. A product would paint these as they arrive.",
                "messages": [],
                "trace": [],
                "stream": steps,
            }
        ],
    }
