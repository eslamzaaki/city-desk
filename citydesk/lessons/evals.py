"""Station 12 — an eval is a dataset, a task, and a grader."""

from __future__ import annotations

from langchain.agents import create_agent

from citydesk.model import DeskChatModel
from citydesk.serialize import message_text
from citydesk.tools import search_archive

META = {
    "id": "evals",
    "number": "12",
    "title": "Evals",
    "kicker": "Dataset, task, grader",
    "summary": (
        "An evaluation is three pieces: a dataset of cases, a task that runs the agent, "
        "and a grader that scores the output. This station grades grounding. A question "
        "passes when the agent called the archive and the answer contains a fact that "
        "lives in the note. A greeting passes when it did not call the archive. LangSmith "
        "hosts this same loop — datasets, experiments, traces — when you want it online. "
        "The shape does not change."
    ),
    "look_for": [
        "The grader checks the tool transcript, not a vibe.",
        "A greeting that searches the archive would fail, even with a polite answer.",
        "Add a row to CASES and you have a regression test for the desk.",
    ],
    "default_prompt": "",
    "accepts_prompt": False,
    "source": "citydesk/lessons/evals.py",
}

CASES = [
    {"question": "When does harbor dredging start?", "needle": "Monday", "expect_tool": True},
    {"question": "Where did the corniche flood?", "needle": "kilometre", "expect_tool": True},
    {"question": "What is the new tram stop called?", "needle": "Customs", "expect_tool": True},
    {"question": "hello", "needle": "City desk is open", "expect_tool": False},
]


def run(prompt: str | None = None) -> dict:
    del prompt
    agent = create_agent(
        model=DeskChatModel(),
        tools=[search_archive],
        system_prompt="Answer from the archive. If there is nothing to look up, do not search.",
    )
    rows = []
    passed = 0
    for case in CASES:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": case["question"]}]},
            {"recursion_limit": 20},
        )
        tools = []
        for message in result["messages"]:
            for call in getattr(message, "tool_calls", None) or []:
                tools.append(call["name"])
        reply = message_text(result["messages"][-1])
        used_tool = "search_archive" in tools
        grounded = case["needle"].lower() in reply.lower()
        grade = "pass" if grounded and used_tool == case["expect_tool"] else "fail"
        if grade == "pass":
            passed += 1
        rows.append(
            [
                case["question"],
                "search_archive" if used_tool else "—",
                case["needle"],
                grade,
            ]
        )
    return {
        "headline": f"{passed} of {len(CASES)} cases passed.",
        "sections": [
            {
                "label": "Grounding grader",
                "body": "Task: the agent. Dataset: the four rows. Grader: needle present, tool policy respected.",
                "messages": [],
                "trace": [],
                "table": {
                    "columns": ["Question", "Tool", "Needle", "Grade"],
                    "rows": rows,
                },
            }
        ],
    }
