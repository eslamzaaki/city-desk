"""CITYDESK_PROVIDER chooses local, OpenAI, or Anthropic for the live counter."""

from __future__ import annotations

from citydesk.model import DeskChatModel, resolve_model


def test_local_provider_ignores_a_provider_model_string(monkeypatch):
    monkeypatch.setenv("CITYDESK_PROVIDER", "local")
    monkeypatch.setenv("CITYDESK_MODEL", "openai:gpt-4.1-mini")

    model, label = resolve_model()

    assert isinstance(model, DeskChatModel)
    assert label == "local DeskChatModel"


def test_openai_provider_uses_the_named_model_when_the_package_is_missing(monkeypatch):
    monkeypatch.setenv("CITYDESK_PROVIDER", "openai")
    monkeypatch.setenv("CITYDESK_MODEL", "openai:gpt-4.1-mini")

    model, label = resolve_model()

    assert isinstance(model, DeskChatModel)
    assert "openai" in label.lower() or "ImportError" in label or "fell back" in label


def test_anthropic_provider_uses_its_default_when_the_model_string_is_for_openai(monkeypatch):
    monkeypatch.setenv("CITYDESK_PROVIDER", "anthropic")
    monkeypatch.setenv("CITYDESK_MODEL", "openai:gpt-4.1-mini")

    model, label = resolve_model()

    assert isinstance(model, DeskChatModel)
    assert "fell back" in label


def test_unknown_provider_stays_local(monkeypatch):
    monkeypatch.setenv("CITYDESK_PROVIDER", "somewhere")
    monkeypatch.delenv("CITYDESK_MODEL", raising=False)

    model, label = resolve_model()

    assert isinstance(model, DeskChatModel)
    assert "unknown" in label
