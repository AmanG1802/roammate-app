"""LLM client for the Brainstorm Chat surface."""
from __future__ import annotations

from typing import Any

from app.services.llm.clients.base import BaseLLMClient


class BrainstormChatClient(BaseLLMClient):
    """Serves ``BrainstormChat`` -- multi-turn chat + extract items."""

    async def chat(
        self,
        history: list[dict[str, str]],
        user_message: str,
        trip_id: int | None = None,
    ) -> str:
        context: dict[str, Any] = {"source": "brainstorm"}
        if trip_id is not None:
            context["trip_id"] = trip_id
        return await self._service.chat(history, user_message, context=context)

    async def extract_items(
        self,
        history: list[dict[str, str]],
        trip_id: int | None = None,
    ) -> list[dict[str, Any]]:
        context: dict[str, Any] = {"source": "brainstorm"}
        if trip_id is not None:
            context["trip_id"] = trip_id
        return await self._service.extract_items(history, context=context)
