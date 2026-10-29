"""The order of the workshop. The assignment is the map; the desk is the job."""

from __future__ import annotations

from typing import Any

from citydesk.lessons import (
    agents,
    evals,
    graphs,
    memory,
    messages,
    middleware_station,
    models,
    retrieval,
    review,
    streaming,
    structured,
    tools_station,
)

ASSIGNMENT = {
    "id": "assignment",
    "number": "00",
    "title": "The assignment",
    "kicker": "One newsroom, every new LangChain surface",
    "summary": "Why this is the project, and which station teaches which feature.",
    "look_for": [],
    "default_prompt": "",
    "accepts_prompt": False,
    "kind": "reading",
    "source": "citydesk/desk.py",
    "paragraphs": [
        "The project is The City Desk, a small newsroom for the port city of Marsa. You are the editor. The assistant on the harbor desk searches a local archive, remembers a reporter’s beat across shifts, and files a brief only after you approve it.",
        "That job is small enough to finish and wide enough to force the parts of LangChain that changed in the 1.0 line. Each station runs real library code. The last station is a shift: the same objects, composed, with you in the loop.",
        "Nothing here calls a model provider. DeskChatModel implements the same interface as the object init_chat_model returns, so every tool call is visible. When you want a live model, set CITYDESK_MODEL to a provider string such as openai:gpt-4.1-mini and install that provider’s package. The stations stay the same.",
        "The next shift, when you want to keep building: swap InMemorySaver for a database checkpointer, send the trace to LangSmith, and register MCP tools beside search_archive. The desk is the place those land, because the seams are already the real ones.",
    ],
    "features": [
        {"name": "Messages and content blocks", "station": "messages"},
        {"name": "init_chat_model, stream, batch", "station": "models"},
        {"name": "@tool and ToolRuntime", "station": "tools"},
        {"name": "ToolStrategy structured output", "station": "structured"},
        {"name": "create_agent", "station": "agents"},
        {"name": "stream_mode updates", "station": "streaming"},
        {"name": "Middleware, PII, fallback, retries, todos", "station": "middleware"},
        {"name": "Checkpointer and store", "station": "memory"},
        {"name": "Human-in-the-loop interrupts", "station": "review"},
        {"name": "Splitters, embeddings, vector stores", "station": "retrieval"},
        {"name": "StateGraph and agent-as-a-node", "station": "graphs"},
        {"name": "Evals: dataset, task, grader", "station": "evals"},
        {"name": "The shift, with you approving the spike", "station": "desk"},
    ],
}

DESK = {
    "id": "desk",
    "number": "13",
    "title": "The desk",
    "kicker": "Work a shift",
    "summary": (
        "Ask about Marsa, save a beat, open a new shift, and file a brief. "
        "Filing waits for you. Preferences stick to the reporter, not the thread."
    ),
    "look_for": [
        "A new shift forgets the transcript and keeps the beat.",
        "An email address is redacted before the model sees it.",
        "File a brief, then approve, edit, or reject it. Search does not wait for you.",
    ],
    "default_prompt": "When does harbor dredging start?",
    "accepts_prompt": True,
    "kind": "desk",
    "source": "citydesk/desk.py",
    "paragraphs": [],
    "features": [],
}

_STATIONS = [
    messages,
    models,
    tools_station,
    structured,
    agents,
    streaming,
    middleware_station,
    memory,
    review,
    retrieval,
    graphs,
    evals,
]

LESSONS: list[dict[str, Any]] = [ASSIGNMENT]
for station in _STATIONS:
    LESSONS.append({**station.META, "kind": "lesson", "paragraphs": [], "features": [], "run": station.run})
LESSONS.append(DESK)

_BY_ID = {lesson["id"]: lesson for lesson in LESSONS}


def list_lessons() -> list[dict[str, Any]]:
    return [_public(lesson) for lesson in LESSONS]


def get_lesson(lesson_id: str) -> dict[str, Any]:
    try:
        return _BY_ID[lesson_id]
    except KeyError as exc:
        raise KeyError(lesson_id) from exc


def run_lesson(lesson_id: str, prompt: str | None = None) -> dict[str, Any]:
    lesson = get_lesson(lesson_id)
    runner = lesson.get("run")
    if runner is None:
        raise ValueError(f"{lesson_id} is not a one-shot station.")
    return {"lesson": _public(lesson), "result": runner(prompt)}


def _public(lesson: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in lesson.items() if key != "run"}
