"""RoammateServiceV1 — the first concrete LLM service strategy.

Pipeline for each method:
  pre-process → prompt builder → model.complete(schema) → parse → field map

When ``LLM_ENABLED`` is False the service returns deterministic Bangkok
fallback data so the full pipeline exercises real code paths without an
API key.

Prompt templates and per-version assets live alongside this module under
``./prompts`` — they are versioned with the service strategy.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.time_categories import TIME_CATEGORY_DEFAULTS
from app.schemas.llm import LLMExtractResponse, LLMItem, LLMPlanResponse
from app.services.llm.fallbacks import (
    BANGKOK_FALLBACK_ITEMS,
    CHAT_FALLBACK_REPLY,
    THAILAND_PLAN_FALLBACK,
)
from app.services.llm.models.base import BaseLLMModel, LLMResponse
from app.services.llm.pre_processor import PreExtracted, pre_extract
from app.services.llm.services.base import BaseLLMService
from app.services.llm.token_tracker import track as track_tokens

log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

HISTORY_TRIM_COUNT = 6


# ── Prompt loading ───────────────────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    """Load a prompt template file from the v1 prompts directory."""
    path = _PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")


# ── Field mapping ────────────────────────────────────────────────────────────

def llm_item_to_brainstorm(item: LLMItem) -> dict[str, Any]:
    """Map an abbreviated LLMItem to a BrainstormBinItem-compatible dict.

    Google Places fields are intentionally left None — enrichment happens
    at commit time (extract/promote endpoints), not during chat.
    """
    return {
        "title": item.t,
        "description": item.d or None,
        "category": item.cat.value,
        "time_category": item.tc,
        "time_hint": TIME_CATEGORY_DEFAULTS.get(item.tc),
        "price_level": item.price,
        "types": item.tags or None,
        "place_id": None,
        "lat": None,
        "lng": None,
        "address": None,
        "photo_url": None,
        "rating": None,
        "opening_hours": None,
        "phone": None,
        "website": None,
        "url_source": None,
    }


def _trim_history(
    history: list[dict[str, str]],
    max_messages: int = HISTORY_TRIM_COUNT,
) -> list[dict[str, str]]:
    """Keep the last *max_messages* entries (~3 user/assistant turns)."""
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def _pack_trip_context(context: dict[str, Any] | None) -> str:
    """Build a compact pipe-delimited context string for concierge.

    Expects context keys: events_today (list[dict]), upcoming (list[dict]),
    role (str), members (list[str]).
    """
    if not context:
        return ""
    parts: list[str] = []
    events_today = context.get("events_today", [])
    if events_today:
        event_strs = [
            f"{e.get('time', '?')} {e.get('title', '?')} ({e.get('duration', '?')}min)"
            for e in events_today[:8]
        ]
        parts.append("Today: " + " | ".join(event_strs))
    upcoming = context.get("upcoming", [])
    if upcoming:
        up_strs = [
            f"{e.get('title', '?')} ({e.get('day', '?')})"
            for e in upcoming[:3]
        ]
        parts.append("Next: " + " | ".join(up_strs))
    role = context.get("role")
    if role:
        parts.append(f"Role: {role}")
    return "\n".join(parts)


def _log_and_track(
    op: str,
    response: LLMResponse,
    context: dict[str, Any] | None = None,
) -> None:
    ctx = context or {}
    track_tokens(
        response,
        operation=op,
        user_id=ctx.get("user_id"),
        trip_id=ctx.get("trip_id"),
        source=ctx.get("source"),
    )


class RoammateServiceV1(BaseLLMService):
    """V1 strategy: pre-process → prompt → model.complete(schema) → parse → map."""

    def __init__(self, model: BaseLLMModel):
        super().__init__(model)

    # ── chat ────────────────────────────────────────────────────────────

    async def chat(
        self,
        history: list[dict[str, str]],
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        if not settings.LLM_ENABLED:
            return CHAT_FALLBACK_REPLY

        pre = pre_extract(user_message)
        context_block = pre.to_context_block()

        source = (context or {}).get("source", "brainstorm")
        if source == "concierge":
            template = _load_prompt("concierge_v1.txt")
            trip_ctx = _pack_trip_context(context)
            system_prompt = template.replace("{trip_context}", trip_ctx).replace(
                "{context_block}", context_block
            )
        else:
            template = _load_prompt("brainstorm_chat_v1.txt")
            system_prompt = template.replace("{context_block}", context_block)

        trimmed = _trim_history(history)
        messages = [
            {"role": "system", "content": system_prompt},
            *trimmed,
            {"role": "user", "content": user_message},
        ]

        # No max_tokens override → model falls back to BaseLLMModel.DEFAULT_MAX_TOKENS.
        response = await self._model.complete(messages)
        _log_and_track("chat", response, context)
        return response.content

    # ── extract ─────────────────────────────────────────────────────────

    async def extract_items(
        self,
        history: list[dict[str, str]],
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not settings.LLM_ENABLED:
            return [dict(item) for item in BANGKOK_FALLBACK_ITEMS]

        system_prompt = _load_prompt("brainstorm_extract_v1.txt")
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
        ]

        response = await self._model.complete(
            messages,
            response_schema=LLMExtractResponse,
            temperature=0.3,
            max_tokens=settings.LLM_MAX_TOKENS_EXTRACT,
        )
        _log_and_track("extract", response, context)

        try:
            data = json.loads(response.content)
            parsed = LLMExtractResponse(**data)
            return [llm_item_to_brainstorm(item) for item in parsed.items]
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            log.warning("LLM extract parse failed (%s), using fallback", exc)
            return [dict(item) for item in BANGKOK_FALLBACK_ITEMS]

    # ── plan_trip ───────────────────────────────────────────────────────

    async def plan_trip(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not settings.LLM_ENABLED:
            return {
                **THAILAND_PLAN_FALLBACK,
                "items": [dict(item) for item in BANGKOK_FALLBACK_ITEMS],
            }

        pre = pre_extract(prompt)
        context_block = pre.to_context_block()

        city = pre.city or "the destination"
        country = pre.country or ""
        num_days = pre.num_days or 3
        num_items = max(num_days * 3, 8)
        budget_tier = pre.budget_tier or "mid"

        template = _load_prompt("plan_trip_v1.txt")
        system_prompt = (
            template
            .replace("{context_block}", context_block)
            .replace("{city}", city)
            .replace("{country}", country)
            .replace("{num_items}", str(num_items))
            .replace("{budget_tier}", budget_tier)
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await self._model.complete(
            messages,
            response_schema=LLMPlanResponse,
            temperature=0.7,
            max_tokens=settings.LLM_MAX_TOKENS_PLAN,
        )
        _log_and_track("plan_trip", response, context)

        try:
            data = json.loads(response.content)
            parsed = LLMPlanResponse(**data)
            return {
                "trip_name": parsed.trip_name,
                "start_date": pre.start_date.isoformat() if pre.start_date else None,
                "duration_days": parsed.duration_days,
                "items": [llm_item_to_brainstorm(item) for item in parsed.items],
            }
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            log.warning("LLM plan_trip parse failed (%s), using fallback", exc)
            return {
                **THAILAND_PLAN_FALLBACK,
                "items": [dict(item) for item in BANGKOK_FALLBACK_ITEMS],
            }
