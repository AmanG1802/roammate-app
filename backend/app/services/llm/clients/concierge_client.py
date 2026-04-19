"""LLM client for the Chat Now (Concierge) surface on the live trip page."""
from __future__ import annotations

from typing import Any

from app.services.llm.clients.base import BaseLLMClient


class ConciergeChatClient(BaseLLMClient):
    """Serves the Chat Now concierge on the live trip page.

    ``trip_context`` carries today's events, user role, trip members,
    and active day so the concierge can reason about the current plan.
    """

    async def chat(
        self,
        history: list[dict[str, str]],
        user_message: str,
        trip_context: dict[str, Any] | None = None,
    ) -> str:
        context: dict[str, Any] = {"source": "concierge"}
        if trip_context:
            context.update(trip_context)
        return await self._service.chat(history, user_message, context=context)
