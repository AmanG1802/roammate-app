"""Unit tests for app.services.llm.registry — model/service factory functions.

Tests build_model, build_service, and client factories with mocked settings.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.llm.registry import (
    build_model,
    build_service,
    get_brainstorm_client,
    get_concierge_client,
    get_dashboard_client,
    _MODEL_MAP,
    _KEY_MAP,
)
from app.services.llm.models.base import BaseLLMModel
from app.services.llm.models.openai_model import OpenAIModel
from app.services.llm.models.claude_model import ClaudeModel
from app.services.llm.models.gemini_model import GeminiModel
from app.services.llm.services.base import BaseLLMService
from app.services.llm.services.v1.roammate_v1 import RoammateServiceV1
from app.services.llm.clients.brainstorm_client import BrainstormChatClient
from app.services.llm.clients.concierge_client import ConciergeChatClient
from app.services.llm.clients.dashboard_client import DashboardClient


class TestModelMap:
    def test_model_map(self):
        # Test 1a - All three providers are registered
        assert "openai" in _MODEL_MAP
        assert "claude" in _MODEL_MAP
        assert "gemini" in _MODEL_MAP

        # Test 1b - Correct class mapping
        assert _MODEL_MAP["openai"] is OpenAIModel
        assert _MODEL_MAP["claude"] is ClaudeModel
        assert _MODEL_MAP["gemini"] is GeminiModel

        # Test 1c - All mapped classes are subclasses of BaseLLMModel
        for cls in _MODEL_MAP.values():
            assert issubclass(cls, BaseLLMModel)


class TestBuildModel:
    @patch("app.services.llm.registry.settings")
    def test_build_model_openai(self, mock_settings):
        # Test 1a - OpenAI provider builds correctly
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        model = build_model()
        assert isinstance(model, OpenAIModel)

    @patch("app.services.llm.registry.settings")
    def test_build_model_claude(self, mock_settings):
        # Test 1b - Claude provider builds correctly
        mock_settings.LLM_PROVIDER = "claude"
        mock_settings.LLM_MODEL = "claude-sonnet-4-20250514"
        mock_settings.ANTHROPIC_API_KEY = "sk-ant-test"
        model = build_model()
        assert isinstance(model, ClaudeModel)

    @patch("app.services.llm.registry.settings")
    def test_build_model_gemini(self, mock_settings):
        # Test 1c - Gemini provider builds correctly
        mock_settings.LLM_PROVIDER = "gemini"
        mock_settings.LLM_MODEL = "gemini-2.0-flash"
        mock_settings.GEMINI_API_KEY = "test-gemini-key"
        model = build_model()
        assert isinstance(model, GeminiModel)

    @patch("app.services.llm.registry.settings")
    def test_build_model_unknown_provider(self, mock_settings):
        # Test 1d - Unknown provider raises ValueError
        mock_settings.LLM_PROVIDER = "unknown_provider"
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            build_model()

    @patch("app.services.llm.registry.settings")
    def test_build_model_empty_api_key(self, mock_settings):
        # Test 1e - None API key defaults to empty string (doesn't crash)
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.OPENAI_API_KEY = None
        model = build_model()
        assert isinstance(model, OpenAIModel)


class TestBuildService:
    def test_build_service_with_model(self):
        # Test 1a - Build service with a provided model
        mock_model = MagicMock(spec=BaseLLMModel)
        service = build_service(mock_model)
        assert isinstance(service, RoammateServiceV1)
        assert service.model is mock_model

    @patch("app.services.llm.registry.build_model")
    def test_build_service_without_model(self, mock_build_model):
        # Test 1b - Build service without model auto-calls build_model
        mock_model = MagicMock(spec=BaseLLMModel)
        mock_build_model.return_value = mock_model
        service = build_service()
        mock_build_model.assert_called_once()
        assert isinstance(service, RoammateServiceV1)


class TestClientFactories:
    @patch("app.services.llm.registry.build_service")
    def test_get_brainstorm_client(self, mock_build_service):
        # Test 1a - Returns BrainstormChatClient instance
        mock_service = MagicMock(spec=BaseLLMService)
        mock_build_service.return_value = mock_service
        client = get_brainstorm_client()
        assert isinstance(client, BrainstormChatClient)

    @patch("app.services.llm.registry.build_service")
    def test_get_concierge_client(self, mock_build_service):
        # Test 1b - Returns ConciergeChatClient instance
        mock_service = MagicMock(spec=BaseLLMService)
        mock_build_service.return_value = mock_service
        client = get_concierge_client()
        assert isinstance(client, ConciergeChatClient)

    @patch("app.services.llm.registry.build_service")
    def test_get_dashboard_client(self, mock_build_service):
        # Test 1c - Returns DashboardClient instance
        mock_service = MagicMock(spec=BaseLLMService)
        mock_build_service.return_value = mock_service
        client = get_dashboard_client()
        assert isinstance(client, DashboardClient)
