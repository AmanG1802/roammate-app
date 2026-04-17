"""Unit tests for NLPService."""
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.nlp_service import NLPService
from app.core.config import settings


async def test_no_api_key_returns_stub(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    svc = NLPService()
    result = await svc.parse_quick_add("Dinner")
    assert result == {"title": "Dinner", "start_time": None, "event_type": "activity"}


async def test_with_api_key_calls_openai(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    svc = NLPService()

    fake_msg = MagicMock()
    fake_msg.content = json.dumps({"title": "Colosseum", "event_type": "activity"})
    fake_choice = MagicMock(message=fake_msg)
    fake_response = MagicMock(choices=[fake_choice])

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)
    svc._client = fake_client

    result = await svc.parse_quick_add("Colosseum tour")
    assert result["title"] == "Colosseum"
    fake_client.chat.completions.create.assert_awaited_once()


async def test_client_is_lazy(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    svc = NLPService()
    assert svc._client is None
    # stub path should not touch the client
    await svc.parse_quick_add("x")
    assert svc._client is None
