"""Station 01 — messages are typed objects with content blocks."""

from __future__ import annotations

from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from citydesk.serialize import dump_message

META = {
    "id": "messages",
    "number": "01",
    "title": "Messages",
    "kicker": "The unit every other feature passes around",
    "summary": (
        "Agents, tools, and middleware do not pass strings. They pass a list of "
        "messages. A message has a type — system, human, ai, tool — and its content "
        "is a list of blocks. Text, a tool call, and a citation can share one message "
        "without a side channel."
    ),
    "look_for": [
        "HumanMessage, AIMessage, and ToolMessage are different types, not roles painted on a dict.",
        "content_blocks is the normalized view, whether you passed a string or a list of blocks.",
        "A tool result points back at the model's call with tool_call_id. That pairing is the agent loop.",
    ],
    "default_prompt": "The corniche is under water around kilometre 3.",
    "accepts_prompt": True,
    "source": "citydesk/lessons/messages.py",
}


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    system = SystemMessage("You are the assistant on the harbor desk. Cite the archive.")
    human = HumanMessage(content=[{"type": "text", "text": text}])
    call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_archive",
                "args": {"query": text},
                "id": "call_demo",
                "type": "tool_call",
            }
        ],
    )
    tool = ToolMessage(
        content="[Corniche flood] Water reached the shop thresholds between kilometre 2 and kilometre 4.",
        tool_call_id="call_demo",
        name="search_archive",
    )
    final = AIMessage(
        content="The corniche flooded between kilometre 2 and kilometre 4. The upper walk stayed dry."
    )
    messages = [system, human, call, tool, final]
    return {
        "headline": "Four message types, one turn. This is the object the rest of the desk edits.",
        "sections": [
            {
                "label": "A turn, written by hand",
                "body": (
                    "Nothing called a model. These objects are what create_agent will "
                    "append for you in the later stations. Open the wire and read content_blocks "
                    "on the human message — the string you typed is a text block."
                ),
                "messages": [dump_message(message) for message in messages],
                "trace": [],
            }
        ],
    }
