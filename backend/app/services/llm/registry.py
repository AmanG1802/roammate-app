"""Factory functions that wire Model -> Service -> Client from config.

Usage in endpoints::

    from app.services.llm.registry import get_brainstorm_client
    client = get_brainstorm_client()
    result = await client.chat(history, message, trip_id=trip_id)

Switching the underlying provider or service strategy is a config change
(``LLM_PROVIDER``, ``LLM_MODEL``) — no endpoint code needs to change.
"""
from __future__ import annotations

from typing import Callable

from app.core.config import settings
from app.services.llm.clients.brainstorm_client import BrainstormChatClient
from app.services.llm.clients.concierge_client import ConciergeChatClient
from app.services.llm.clients.dashboard_client import DashboardClient
from app.services.llm.models.base import BaseLLMModel
from app.services.llm.models.claude_model import ClaudeModel
from app.services.llm.models.gemini_model import GeminiModel
from app.services.llm.models.openai_model import OpenAIModel
from app.services.llm.services.base import BaseLLMService
from app.services.llm.services.roammate_v1 import RoammateServiceV1

_MODEL_MAP: dict[str, type[BaseLLMModel]] = {
    "openai": OpenAIModel,
    "claude": ClaudeModel,
    "gemini": GeminiModel,
}

_KEY_MAP: dict[str, Callable[[], str | None]] = {
    "openai": lambda: settings.OPENAI_API_KEY,
    "claude": lambda: settings.ANTHROPIC_API_KEY,
    "gemini": lambda: settings.GEMINI_API_KEY,
}


def build_model() -> BaseLLMModel:
    """Instantiate the model wrapper for the configured provider."""
    provider = settings.LLM_PROVIDER
    model_cls = _MODEL_MAP.get(provider)
    if model_cls is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER={provider!r}. "
            f"Choose from: {', '.join(_MODEL_MAP)}"
        )
    api_key = (_KEY_MAP[provider]()) or ""
    return model_cls(api_key=api_key, model=settings.LLM_MODEL)


def build_service(model: BaseLLMModel | None = None) -> BaseLLMService:
    """Instantiate the active service strategy."""
    if model is None:
        model = build_model()
    return RoammateServiceV1(model)


def get_dashboard_client() -> DashboardClient:
    return DashboardClient(build_service())


def get_brainstorm_client() -> BrainstormChatClient:
    return BrainstormChatClient(build_service())


def get_concierge_client() -> ConciergeChatClient:
    return ConciergeChatClient(build_service())
