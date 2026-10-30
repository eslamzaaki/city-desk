"""The API process picks up a repo-root .env file."""

from __future__ import annotations

import os

from citydesk.envfile import load_env


def test_load_env_sets_missing_variables(tmp_path, monkeypatch):
    monkeypatch.delenv("CITYDESK_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CITYDESK_MODEL=openai:gpt-4.1-mini\nOPENAI_API_KEY=test-key\n",
        encoding="utf-8",
    )

    assert load_env(env_file) is True
    assert os.environ["CITYDESK_MODEL"] == "openai:gpt-4.1-mini"
    assert os.environ["OPENAI_API_KEY"] == "test-key"


def test_load_env_leaves_existing_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("CITYDESK_MODEL", "")
    env_file = tmp_path / ".env"
    env_file.write_text("CITYDESK_MODEL=openai:gpt-4.1-mini\n", encoding="utf-8")

    load_env(env_file)

    assert os.environ["CITYDESK_MODEL"] == ""


def test_missing_env_file_is_fine(tmp_path):
    assert load_env(tmp_path / ".env") is False
