"""Station 08 — a checkpointer remembers the shift, a store remembers the reporter."""

from __future__ import annotations

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from citydesk.lessons.support import pack
from citydesk.model import DeskChatModel
from citydesk.schemas import DeskContext
from citydesk.tools import recall_preferences, save_preference
from citydesk.tracing import trace_scope

META = {
    "id": "memory",
    "number": "08",
    "title": "Memory",
    "kicker": "Thread state and cross-thread store",
    "summary": (
        "Short-term memory is the checkpointer. Pass a thread id and the message list "
        "for that shift is still there on the next invoke. Long-term memory is the store. "
        "It is keyed by a namespace you choose — here, the reporter's name — and it is "
        "visible from every thread. A new shift does not see the old transcript. It can "
        "still recall the beat, because the tool reads the store."
    ),
    "look_for": [
        "Shift A’s second turn still contains the first message. That is the checkpointer.",
        "Shift B is a new thread. The transcript starts over. The beat is still there.",
        "Hana’s shift uses the same store and a different namespace, so Nour’s note is absent.",
    ],
    "default_prompt": "",
    "accepts_prompt": False,
    "source": "citydesk/lessons/memory.py",
}


def run(prompt: str | None = None) -> dict:
    del prompt
    saver = InMemorySaver()
    store = InMemoryStore()
    agent = create_agent(
        model=DeskChatModel(),
        tools=[save_preference, recall_preferences],
        system_prompt="Save and recall reporter preferences with the tools.",
        checkpointer=saver,
        store=store,
        context_schema=DeskContext,
    )
    sections = [
        _turn(agent, "shift-a", "Remember that my beat is the night market.", "Nour El-Sayed", "Saved on this shift"),
        _turn(agent, "shift-a", "What is my beat?", "Nour El-Sayed", "Same shift asks again"),
        _turn(agent, "shift-b", "What is my beat?", "Nour El-Sayed", "New shift, same reporter"),
        _turn(agent, "shift-c", "What is my beat?", "Hana Farid", "New shift, other reporter"),
    ]
    return {
        "headline": "The transcript is per shift. The beat note is per reporter.",
        "sections": sections,
    }


def _turn(agent, thread_id: str, text: str, reporter: str, label: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
    with trace_scope() as events:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": text}]},
            config,
            context=DeskContext(reporter=reporter, desk="harbor"),
        )
    return pack(
        result,
        events,
        label=f"{label} · {thread_id} · {reporter}",
        body=text,
    )
