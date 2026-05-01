"""Base class for LLM service strategies.

A service orchestrates pre-processing, the LLM call itself, and
post-processing.  Different concrete services (V1, V2, ...) can
implement different strategies while keeping the same interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.services.llm.models.base import BaseLLMModel


class BaseLLMService(ABC):
    """Strategy that wraps a model and adds domain-specific logic."""

    def __init__(self, model: BaseLLMModel):
        self._model = model

    @property
    def model(self) -> BaseLLMModel:
        return self._model

    @abstractmethod
    async def chat(
        self,
        history: list[dict[str, str]],
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Conversational turn. Returns assistant text."""
        ...

    @abstractmethod
    async def extract_items(
        self,
        history: list[dict[str, str]],
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract structured brainstorm items from a conversation."""
        ...

    @abstractmethod
    async def plan_trip(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a trip plan from a free-form prompt."""
        ...
