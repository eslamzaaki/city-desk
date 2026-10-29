"""HTTP surface for the stations and the live shift."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from citydesk.lessons.catalog import get_lesson, list_lessons, run_lesson
from citydesk.service import read_thread, resume_turn, take_turn

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "web" / "dist"
SOURCE_ROOT = (ROOT / "citydesk").resolve()

app = FastAPI(title="The City Desk", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunIn(BaseModel):
    prompt: str | None = None


class TurnIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=2000)
    reporter: str = Field(default="Nour El-Sayed", min_length=1, max_length=80)
    desk: str = Field(default="harbor", min_length=1, max_length=40)


class ResumeIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=80)
    decisions: list[dict]
    reporter: str = Field(default="Nour El-Sayed", min_length=1, max_length=80)
    desk: str = Field(default="harbor", min_length=1, max_length=40)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "open", "desk": "harbor"}


@app.get("/api/lessons")
def lessons() -> dict:
    return {"lessons": list_lessons()}


@app.post("/api/lessons/{lesson_id}/run")
def run(lesson_id: str, body: RunIn) -> dict:
    try:
        get_lesson(lesson_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No such station.") from exc
    try:
        return run_lesson(lesson_id, body.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.get("/api/lessons/{lesson_id}/source")
def source(lesson_id: str) -> dict[str, str]:
    try:
        lesson = get_lesson(lesson_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No such station.") from exc
    relative = lesson.get("source") or ""
    path = (ROOT / relative).resolve()
    if not str(path).startswith(str(SOURCE_ROOT)) or not path.is_file():
        raise HTTPException(status_code=404, detail="No source for this station.")
    return {"path": relative, "code": path.read_text(encoding="utf-8")}


@app.post("/api/desk/turn")
def desk_turn(body: TurnIn) -> dict:
    try:
        return take_turn(body.thread_id.strip(), body.message.strip(), body.reporter.strip(), body.desk.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.post("/api/desk/resume")
def desk_resume(body: ResumeIn) -> dict:
    try:
        return resume_turn(body.thread_id.strip(), body.decisions, body.reporter.strip(), body.desk.strip())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="That shift does not exist.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.get("/api/desk/state")
def desk_state(thread_id: str, reporter: str = "Nour El-Sayed", desk: str = "harbor") -> dict:
    try:
        return read_thread(thread_id, reporter, desk)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


if DIST.exists():
    assets = DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        candidate = (DIST / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(DIST.resolve())):
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
