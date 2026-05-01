"""§1B — RoammateServiceV1 envelope parsing and persona injection.

Verifies the v1 service:
  - Falls back gracefully on bad LLM output.
  - Trims chat history to budget.
  - Packs persona descriptors into the system prompt.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm.models.base import LLMResponse
from app.services.llm.services.v1.roammate_v1 import (
    HISTORY_TRIM_COUNT,
    RoammateServiceV1,
    _pack_user_persona,
    _trim_history,
    llm_item_to_brainstorm,
)


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.provider_name.return_value = "openai"
    model.model_name.return_value = "gpt-4o-mini"
    return model


# ── Envelope parsing tests ────────────────────────────────────────────────────


async def test_extract_items_invalid_json_triggers_fallback(monkeypatch, mock_model):
    monkeypatch.setattr("app.core.config.settings.LLM_ENABLED", True)
    mock_model.complete = AsyncMock(
        return_value=LLMResponse(
            content="NOT VALID JSON {{{",
            input_tokens=10,
            output_tokens=5,
            model="gpt-4o-mini",
            provider="openai",
        )
    )
    svc = RoammateServiceV1(mock_model)
    result = await svc.extract_items(
        [{"role": "user", "content": "test"}],
        context={"source": "brainstorm"},
    )
    # Should return Bangkok fallback items
    assert len(result) == 10
    assert result[0]["title"] == "Thip Samai Pad Thai"


async def test_extract_items_valid_envelope_parses_map_output(monkeypatch, mock_model):
    monkeypatch.setattr("app.core.config.settings.LLM_ENABLED", True)
    envelope = {
        "user_output": "Here are some ideas...",
        "map_output": [
            {
                "t": "Grand Palace",
                "d": "Beautiful temple complex",
                "cat": "Landmarks & Viewpoints",
                "tc": "morning",
                "price": 2,
                "tags": ["landmark"],
            }
        ],
        "trip_name": "Test",
        "duration_days": 3,
    }
    mock_model.complete = AsyncMock(
        return_value=LLMResponse(
            content=json.dumps(envelope),
            input_tokens=50,
            output_tokens=100,
            model="gpt-4o-mini",
            provider="openai",
        )
    )
    svc = RoammateServiceV1(mock_model)
    result = await svc.extract_items(
        [{"role": "user", "content": "suggest Bangkok places"}],
        context={"source": "brainstorm"},
    )
    assert len(result) == 1
    assert result[0]["title"] == "Grand Palace"
    assert result[0]["category"] == "Landmarks & Viewpoints"


async def test_chat_returns_fallback_when_llm_disabled(monkeypatch, mock_model):
    monkeypatch.setattr("app.core.config.settings.LLM_ENABLED", False)
    svc = RoammateServiceV1(mock_model)
    result = await svc.chat([], "test", context={"source": "brainstorm"})
    assert "Bangkok" in result
    mock_model.complete.assert_not_awaited()


# ── History trimming ──────────────────────────────────────────────────────────


def test_trim_history_passes_through_short_list():
    history = [{"role": "user", "content": f"msg{i}"} for i in range(4)]
    assert _trim_history(history) == history


def test_trim_history_trims_long_list():
    history = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
    trimmed = _trim_history(history)
    assert len(trimmed) == HISTORY_TRIM_COUNT
    assert trimmed[-1] == history[-1]


# ── Persona packing ──────────────────────────────────────────────────────────


def test_pack_user_persona_empty_when_personas_null():
    assert _pack_user_persona(None) == ""


def test_pack_user_persona_empty_when_personas_empty_list():
    assert _pack_user_persona([]) == ""


def test_pack_user_persona_includes_descriptors_in_order():
    result = _pack_user_persona(["foodie", "nature_lover"])
    assert "User preferences:" in result
    assert "cuisine" in result.lower()
    assert "parks" in result.lower() or "forest" in result.lower()


def test_pack_user_persona_skips_unknown_slugs_silently():
    result = _pack_user_persona(["foodie", "nonexistent_slug", "nature_lover"])
    assert "User preferences:" in result
    # Should not crash, should include valid ones


def test_pack_user_persona_all_14_returns_nonempty():
    all_slugs = [
        "foodie", "culture_buff", "nature_lover", "adventure_seeker",
        "beach_bum", "history_nerd", "nightlife_enthusiast", "shopaholic",
        "wellness_seeker", "photographer", "family_traveller", "solo_explorer",
        "luxury_traveller", "budget_hacker",
    ]
    result = _pack_user_persona(all_slugs)
    assert len(result) > 0
    assert "User preferences:" in result
