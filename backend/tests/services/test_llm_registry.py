"""§1A — Registry & model selection.

Verifies ``app.services.llm.registry`` builds the correct provider wrapper
based on ``settings.LLM_PROVIDER`` / ``settings.LLM_MODEL`` and that the
client/service composition is wired correctly.
"""
from __future__ import annotations

import pytest

from app.services.llm import registry
from app.services.llm.clients.brainstorm_client import BrainstormChatClient
from app.services.llm.clients.concierge_client import ConciergeChatClient
from app.services.llm.clients.dashboard_client import DashboardClient
from app.services.llm.models.claude_model import ClaudeModel
from app.services.llm.models.gemini_model import GeminiModel
from app.services.llm.models.openai_model import OpenAIModel
from app.services.llm.services.v1.roammate_v1 import RoammateServiceV1


def _set_provider(monkeypatch, provider: str, model: str = "test-model"):
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", provider)
    monkeypatch.setattr("app.core.config.settings.LLM_MODEL", model)
    monkeypatch.setattr("app.core.config.settings.OPENAI_API_KEY", "fake-openai")
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "fake-claude")
    monkeypatch.setattr("app.core.config.settings.GEMINI_API_KEY", "fake-gemini")


def test_build_model_picks_openai(monkeypatch):
    _set_provider(monkeypatch, "openai", "gpt-4o-mini")
    m = registry.build_model()
    assert isinstance(m, OpenAIModel)
    assert m.provider_name() == "openai"
    assert m.model_name() == "gpt-4o-mini"


def test_build_model_picks_claude(monkeypatch):
    _set_provider(monkeypatch, "claude", "claude-sonnet-4-20250514")
    m = registry.build_model()
    assert isinstance(m, ClaudeModel)
    assert m.provider_name() == "claude"


def test_build_model_picks_gemini(monkeypatch):
    _set_provider(monkeypatch, "gemini", "gemini-2.0-flash")
    m = registry.build_model()
    assert isinstance(m, GeminiModel)
    assert m.provider_name() == "gemini"


def test_build_model_unknown_provider_raises(monkeypatch):
    _set_provider(monkeypatch, "bogus")
    with pytest.raises(ValueError) as excinfo:
        registry.build_model()
    assert "bogus" in str(excinfo.value)
    # Error message advertises supported providers so misconfig is fixable
    msg = str(excinfo.value)
    assert "openai" in msg and "claude" in msg and "gemini" in msg


def test_build_model_missing_api_key_passes_empty_string(monkeypatch):
    """A missing key should not crash — the wrapper swaps None for ''."""
    monkeypatch.setattr("app.core.config.settings.LLM_PROVIDER", "openai")
    monkeypatch.setattr("app.core.config.settings.LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setattr("app.core.config.settings.OPENAI_API_KEY", None)
    m = registry.build_model()
    assert isinstance(m, OpenAIModel)
    assert m._api_key == ""


def test_build_service_wraps_model(monkeypatch):
    _set_provider(monkeypatch, "openai")
    svc = registry.build_service()
    assert isinstance(svc, RoammateServiceV1)
    assert svc.model is not None


def test_get_brainstorm_client_returns_brainstorm_client(monkeypatch):
    _set_provider(monkeypatch, "openai")
    c = registry.get_brainstorm_client()
    assert isinstance(c, BrainstormChatClient)
    assert isinstance(c.service, RoammateServiceV1)


def test_get_dashboard_client_returns_dashboard_client(monkeypatch):
    _set_provider(monkeypatch, "openai")
    c = registry.get_dashboard_client()
    assert isinstance(c, DashboardClient)


def test_get_concierge_client_returns_concierge_client(monkeypatch):
    _set_provider(monkeypatch, "openai")
    c = registry.get_concierge_client()
    assert isinstance(c, ConciergeChatClient)


def test_each_call_returns_fresh_instance(monkeypatch):
    """Registry doesn't memoise — switching providers without restart works."""
    _set_provider(monkeypatch, "openai")
    a = registry.build_model()
    _set_provider(monkeypatch, "claude")
    b = registry.build_model()
    assert isinstance(a, OpenAIModel)
    assert isinstance(b, ClaudeModel)
