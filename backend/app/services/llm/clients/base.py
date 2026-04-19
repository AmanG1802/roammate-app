"""Base class for LLM clients.

Each UI surface (Dashboard, Brainstorm Chat, Concierge) gets its own
client subclass.  Clients assemble surface-specific context and
delegate all LLM logic to the injected ``BaseLLMService``.
"""
from __future__ import annotations

from app.services.llm.services.base import BaseLLMService


class BaseLLMClient:
    """One per UI surface.  Owns context building, delegates to a service."""

    def __init__(self, service: BaseLLMService):
        self._service = service

    @property
    def service(self) -> BaseLLMService:
        return self._service
