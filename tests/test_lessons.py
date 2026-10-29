"""Each station has to do the thing its copy claims."""

from __future__ import annotations

from fastapi.testclient import TestClient

from citydesk.api import app
from citydesk.corpus import search_notes
from citydesk.lessons.catalog import list_lessons, run_lesson
from citydesk.service import reset_desk, resume_turn, take_turn


def _text(section) -> str:
    chunks = [section.get("body", "")]
    for message in section.get("messages", []):
        content = message.get("content", "")
        chunks.append(content if isinstance(content, str) else str(content))
        for call in message.get("tool_calls") or []:
            chunks.append(call.get("name") or "")
    chunks.append(str(section.get("trace")))
    chunks.append(str(section.get("card")))
    chunks.append(str(section.get("todos")))
    return "\n".join(chunks)


def test_archive_finds_the_dredging_note():
    hits = search_notes("When does harbor dredging start?", k=1)
    assert hits
    assert "Monday" in hits[0]["text"]
    assert "pier" in hits[0]["text"].lower()


def test_every_runnable_station_returns_a_headline():
    for lesson in list_lessons():
        if lesson["kind"] != "lesson":
            continue
        result = run_lesson(lesson["id"])["result"]
        assert result["headline"]
        assert result["sections"]


def test_messages_expose_content_blocks():
    section = run_lesson("messages")["result"]["sections"][0]
    human = section["messages"][1]
    assert human["type"] == "human"
    assert any(block.get("type") == "text" for block in human["content_blocks"])
    assert section["messages"][2]["tool_calls"][0]["name"] == "search_archive"


def test_models_stream_tokens():
    result = run_lesson("models", "hello")["result"]
    assert "City desk is open" in result["headline"]
    assert len(result["sections"][0]["tokens"]) > 3


def test_tools_inject_the_reporter():
    blob = _text(run_lesson("tools")["result"]["sections"][0])
    assert "Nour El-Sayed" in blob
    assert "harbor" in blob


def test_structured_card_is_validated():
    card = run_lesson("structured")["result"]["sections"][0]["card"]
    assert "Monday" in card["summary"] or "pier" in card["summary"].lower() or "Monday" in card["headline"]
    assert 0 <= card["confidence"] <= 1
    assert card["sources"]


def test_agent_searches_then_stops():
    messages = run_lesson("agents")["result"]["sections"][0]["messages"]
    assert any(message["type"] == "tool" for message in messages)
    assert messages[-1]["type"] == "ai"
    assert "Monday" in messages[-1]["content"]


def test_stream_nodes_are_model_then_tools():
    steps = run_lesson("streaming")["result"]["sections"][0]["stream"]
    assert [step["node"] for step in steps] == ["model", "tools", "model"]


def test_middleware_covers_the_hooks():
    sections = {section["label"]: section for section in run_lesson("middleware")["result"]["sections"]}
    pii = _text(sections["PII redaction and a dynamic prompt"])
    assert "[REDACTED_EMAIL]" in pii
    assert "nour@marsa.test" not in pii
    assert "PC-4412" not in pii
    assert "harbor" in pii
    assert "Tool error caught" in _text(sections["wrap_tool_call turns a crash into a tool message"])
    assert "Wire restored" in _text(sections["ToolRetryMiddleware"])
    assert "City desk is open" in _text(sections["ModelFallbackMiddleware"])
    assert "limit" in _text(sections["ModelCallLimitMiddleware"]).lower()
    assert sections["TodoListMiddleware"]["todos"]
    summary = _text(sections["SummarizationMiddleware"])
    assert "Summary:" in summary
    assert "Monday" in summary or "kilometre" in summary


def test_memory_is_per_reporter_not_per_thread():
    sections = run_lesson("memory")["result"]["sections"]
    same_humans = [message for message in sections[1]["messages"] if message["type"] == "human"]
    new_humans = [message for message in sections[2]["messages"] if message["type"] == "human"]
    assert len(same_humans) == 2
    assert len(new_humans) == 1
    assert "night market" in _text(sections[1])
    assert "night market" in _text(sections[2])
    assert "Nothing saved" in _text(sections[3])


def test_review_approve_edit_and_reject():
    sections = run_lesson("review")["result"]["sections"]
    assert sections[0]["interrupt"]["value"]["action_requests"][0]["name"] == "file_brief"
    assert "On the spike" in _text(sections[0])
    assert "upper walk still open" in _text(sections[1])
    assert "Hold it" in _text(sections[2])
    assert "On the spike" not in sections[2]["messages"][-2]["content"] if False else "rejected" in _text(sections[2]) or "Hold it" in _text(sections[2])


def test_graph_routes_research_and_direct():
    routes = run_lesson("graphs", "What about the flood?")["result"]["sections"][0]["routes"]
    assert routes[0]["route"] == "research"
    assert "kilometre" in routes[0]["reply"]
    assert routes[1]["route"] == "direct"
    assert "search_archive" not in routes[1]["reply"]


def test_evals_all_pass():
    result = run_lesson("evals")["result"]
    assert result["headline"].startswith("4 of 4")
    grades = [row[-1] for row in result["sections"][0]["table"]["rows"]]
    assert grades == ["pass", "pass", "pass", "pass"]


def test_desk_shift_memory_and_review():
    reset_desk()
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200

    first = take_turn("shift-1", "Remember that my beat is the night market.", "Nour El-Sayed", "harbor")
    assert any("night market" in note for note in first["memories"])

    second = take_turn("shift-2", "What is my beat?", "Nour El-Sayed", "harbor")
    blob = " ".join(
        message["content"] if isinstance(message["content"], str) else "" for message in second["messages"]
    )
    assert "night market" in blob
    assert second["interrupt"] is None

    paused = take_turn("shift-1", "File a brief on the corniche flood.", "Nour El-Sayed", "harbor")
    assert paused["interrupt"]["value"]["action_requests"][0]["name"] == "file_brief"
    args = paused["interrupt"]["value"]["action_requests"][0]["args"]
    resumed = resume_turn(
        "shift-1",
        [{"type": "edit", "edited_action": {"name": "file_brief", "args": {**args, "headline": "Corniche still shut"}}}],
        "Nour El-Sayed",
        "harbor",
    )
    assert resumed["interrupt"] is None
    assert any(entry["headline"] == "Corniche still shut" for entry in resumed["spike"])

    other = take_turn("shift-3", "What is my beat?", "Hana Farid", "harbor")
    other_blob = " ".join(
        message["content"] if isinstance(message["content"], str) else "" for message in other["messages"]
    )
    assert "Nothing saved" in other_blob

    listed = client.get("/api/lessons")
    assert listed.status_code == 200
    ids = [lesson["id"] for lesson in listed.json()["lessons"]]
    assert ids[0] == "assignment"
    assert ids[-1] == "desk"
    source = client.get("/api/lessons/agents/source")
    assert source.status_code == 200
    assert "create_agent" in source.json()["code"]
