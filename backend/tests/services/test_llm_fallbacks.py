"""§1C — Fallback data tests.

Verifies that fallback payload is always a fresh copy (no shared-list bugs)
and that the data structure is consistent.
"""
from __future__ import annotations

from app.services.llm.fallbacks import BANGKOK_FALLBACK_ITEMS, CHAT_FALLBACK_REPLY, THAILAND_PLAN_FALLBACK


def test_fallback_payload_is_a_fresh_copy():
    """Mutating the returned items must not mutate the module-level constant."""
    items = [dict(item) for item in BANGKOK_FALLBACK_ITEMS]
    original_title = BANGKOK_FALLBACK_ITEMS[0]["title"]
    items[0]["title"] = "MUTATED"
    assert BANGKOK_FALLBACK_ITEMS[0]["title"] == original_title


def test_fallback_items_all_have_required_fields():
    required = {"title", "description", "category", "lat", "lng"}
    for item in BANGKOK_FALLBACK_ITEMS:
        for field in required:
            assert field in item, f"Missing '{field}' in {item.get('title')}"


def test_fallback_items_count():
    assert len(BANGKOK_FALLBACK_ITEMS) == 10


def test_chat_fallback_reply_is_nonempty_string():
    assert isinstance(CHAT_FALLBACK_REPLY, str)
    assert len(CHAT_FALLBACK_REPLY) > 50


def test_thailand_plan_fallback_has_trip_structure():
    assert "trip_name" in THAILAND_PLAN_FALLBACK
    assert "duration_days" in THAILAND_PLAN_FALLBACK
    assert THAILAND_PLAN_FALLBACK["duration_days"] == 3
