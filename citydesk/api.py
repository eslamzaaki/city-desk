"""HTTP surface for the Lumen counter."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from citydesk.service import approve_candidate, read_thread, record_feedback, resume_turn, take_turn
from citydesk.suggest import build_suggestions, last_report
from citydesk.shop import CUSTOMERS

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "web" / "dist"

app = FastAPI(title="Lumen Counter", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TurnIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=2000)
    customer_id: str = Field(default="sara", min_length=1, max_length=40)


class ResumeIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=80)
    decisions: list[dict]
    customer_id: str = Field(default="sara", min_length=1, max_length=40)


class FeedbackIn(BaseModel):
    thread_id: str = Field(min_length=1, max_length=80)
    customer_id: str = Field(min_length=1, max_length=40)
    response_id: str = Field(min_length=1, max_length=40)
    scope: str = Field(pattern="^(personal|shared)$")
    rating: int = Field(ge=1, le=5)
    reason: str | None = None
    corrected_answer: str | None = None
    consent_for_training: bool = False


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "open", "shop": "lumen"}


@app.get("/api/shop/customers")
def customers() -> dict:
    return {"customers": list(CUSTOMERS.values())}


@app.post("/api/desk/turn")
def desk_turn(body: TurnIn) -> dict:
    try:
        return take_turn(body.thread_id.strip(), body.message.strip(), body.customer_id.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.post("/api/desk/resume")
def desk_resume(body: ResumeIn) -> dict:
    try:
        return resume_turn(body.thread_id.strip(), body.decisions, body.customer_id.strip())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="That chat does not exist.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.get("/api/desk/state")
def desk_state(thread_id: str, customer_id: str = "sara") -> dict:
    try:
        return read_thread(thread_id, customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.post("/api/desk/feedback")
def desk_feedback(body: FeedbackIn) -> dict:
    try:
        return record_feedback(
            body.thread_id.strip(),
            body.customer_id.strip(),
            body.response_id.strip(),
            body.scope,
            body.rating,
            body.reason,
            body.corrected_answer,
            body.consent_for_training,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="That chat does not exist.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.post("/api/desk/suggestions")
def desk_suggestions() -> dict:
    try:
        return build_suggestions()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{exc.__class__.__name__}: {exc}") from exc


@app.get("/api/desk/suggestions")
def desk_suggestions_last() -> dict:
    return last_report()


@app.post("/api/desk/candidates/{candidate_id}/approve")
def desk_approve(candidate_id: str) -> dict:
    try:
        return approve_candidate(candidate_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No such candidate.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
