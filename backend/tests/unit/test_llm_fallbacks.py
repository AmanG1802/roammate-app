"""Unit tests for app.services.llm.fallbacks — deterministic fallback data.

Validates the shape and integrity of static fallback datasets used when LLM_ENABLED=False.
"""
import pytest
from app.services.llm.fallbacks import (
    BANGKOK_FALLBACK_ITEMS,
    THAILAND_PLAN_FALLBACK,
    CHAT_FALLBACK_REPLY,
)


class TestBangkokFallbackItems:
    def test_bangkok_fallback_items(self):
        # Test 1a - Contains exactly 10 items
        assert len(BANGKOK_FALLBACK_ITEMS) == 10

        # Test 1b - Every item has required fields
        required_keys = {"title", "description", "category", "lat", "lng"}
        for item in BANGKOK_FALLBACK_ITEMS:
            for key in required_keys:
                assert key in item, f"Missing key '{key}' in item: {item.get('title')}"

        # Test 1c - All titles are non-empty strings
        for item in BANGKOK_FALLBACK_ITEMS:
            assert isinstance(item["title"], str)
            assert len(item["title"]) > 0

        # Test 1d - Lat/lng are valid coordinate ranges
        for item in BANGKOK_FALLBACK_ITEMS:
            assert -90 <= item["lat"] <= 90
            assert -180 <= item["lng"] <= 180

        # Test 1e - Categories span diverse types (at least 5 unique categories)
        categories = {item["category"] for item in BANGKOK_FALLBACK_ITEMS}
        assert len(categories) >= 5

        # Test 1f - time_category field is present on every item
        for item in BANGKOK_FALLBACK_ITEMS:
            assert "time_category" in item
            assert item["time_category"] is not None

        # Test 1g - price_level is within expected range (0-4)
        for item in BANGKOK_FALLBACK_ITEMS:
            assert "price_level" in item
            assert 0 <= item["price_level"] <= 4

        # Test 1h - At least one item has a place_id and one without
        has_place_id = [i for i in BANGKOK_FALLBACK_ITEMS if i.get("place_id")]
        no_place_id = [i for i in BANGKOK_FALLBACK_ITEMS if not i.get("place_id")]
        assert len(has_place_id) > 0
        assert len(no_place_id) > 0

        # Test 1i - rating field is valid where present
        for item in BANGKOK_FALLBACK_ITEMS:
            if item.get("rating") is not None:
                assert 0.0 <= item["rating"] <= 5.0


class TestThailandPlanFallback:
    def test_thailand_plan_fallback(self):
        # Test 1a - Has trip_name
        assert "trip_name" in THAILAND_PLAN_FALLBACK
        assert isinstance(THAILAND_PLAN_FALLBACK["trip_name"], str)
        assert len(THAILAND_PLAN_FALLBACK["trip_name"]) > 0

        # Test 1b - Has duration_days as positive int
        assert "duration_days" in THAILAND_PLAN_FALLBACK
        assert isinstance(THAILAND_PLAN_FALLBACK["duration_days"], int)
        assert THAILAND_PLAN_FALLBACK["duration_days"] > 0

        # Test 1c - start_date can be None (no fixed date)
        assert "start_date" in THAILAND_PLAN_FALLBACK

        # Test 1d - items list matches BANGKOK_FALLBACK_ITEMS
        assert THAILAND_PLAN_FALLBACK["items"] is BANGKOK_FALLBACK_ITEMS


class TestChatFallbackReply:
    def test_chat_fallback_reply(self):
        # Test 1a - Is a non-empty string
        assert isinstance(CHAT_FALLBACK_REPLY, str)
        assert len(CHAT_FALLBACK_REPLY) > 50

        # Test 1b - Mentions Bangkok (the fallback city)
        assert "Bangkok" in CHAT_FALLBACK_REPLY

        # Test 1c - Contains a user call-to-action
        assert "Brainstorm Bin" in CHAT_FALLBACK_REPLY

        # Test 1d - Mentions multiple items by name
        assert "Thip Samai" in CHAT_FALLBACK_REPLY
        assert "Grand Palace" in CHAT_FALLBACK_REPLY
