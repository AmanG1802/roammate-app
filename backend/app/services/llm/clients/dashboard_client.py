"""LLM client for the Dashboard Trip Planner surface."""
from __future__ import annotations

from typing import Any

from app.services.llm.clients.base import BaseLLMClient


class DashboardClient(BaseLLMClient):
    """Serves ``DashboardTripPlanner`` -- plan a trip from a single prompt."""

    async def plan_trip(self, prompt: str) -> dict[str, Any]:
        context = {"source": "dashboard"}
        return await self._service.plan_trip(prompt, context=context)
