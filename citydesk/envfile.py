"""Read the repo-root ``.env`` into the process environment."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path | None = None) -> bool:
    """Load ``.env``. Variables already set in the environment stay as they are."""

    return load_dotenv(path or ROOT / ".env", override=False)
