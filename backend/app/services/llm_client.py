"""Backward-compatibility shim.

The real implementation now lives in ``app.services.llm.*``.  This
module re-exports the fallback data and provides thin async wrappers
so that existing tests (and any remaining callers) continue to work
without modification.

This file will be removed once all imports are migrated.
"""
from __future__ import annotations

from typing import Any

from app.services.llm.fallbacks import (
    BANGKOK_FALLBACK_ITEMS as _BANGKOK_FALLBACK_ITEMS,
    CHAT_FALLBACK_REPLY as _CHAT_FALLBACK_REPLY,
    THAILAND_PLAN_FALLBACK as _THAILAND_PLAN_FALLBACK,
)
from app.services.llm.registry import get_brainstorm_client, get_dashboard_client

# Re-export so ``from app.services.llm_client import _BANGKOK_FALLBACK_ITEMS`` works.
__all__ = [
    "_BANGKOK_FALLBACK_ITEMS",
    "_CHAT_FALLBACK_REPLY",
    "_THAILAND_PLAN_FALLBACK",
    "chat",
    "extract_items",
    "plan_trip",
]


async def chat(history: list[dict], user_message: str) -> str:
    """Single-turn reply given the running conversation."""
    client = get_brainstorm_client()
    return await client.chat(history, user_message)


async def extract_items(history: list[dict]) -> list[dict[str, Any]]:
    """Turn a chat history into structured brainstorm items."""
    client = get_brainstorm_client()
    return await client.extract_items(history)


async def plan_trip(prompt: str) -> dict[str, Any]:
    """Turn a single free-form prompt into a trip preview + brainstorm item seed."""
    client = get_dashboard_client()
    return await client.plan_trip(prompt)
