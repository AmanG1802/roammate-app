"""Unit tests for llm_client service (LLM_ENABLED=False fallback path)."""
import pytest

from app.services import llm_client
from app.services.llm_client import _BANGKOK_FALLBACK_ITEMS


async def test_chat_returns_fallback_string():
    result = await llm_client.chat([], "Tell me about Bangkok")
    assert isinstance(result, str)
    assert "Bangkok" in result
    assert len(result) > 20


async def test_extract_items_returns_bangkok_list():
    items = await llm_client.extract_items([])
    assert isinstance(items, list)
    assert len(items) == len(_BANGKOK_FALLBACK_ITEMS)
    assert all("title" in it for it in items)


async def test_extract_items_full_fields():
    items = await llm_client.extract_items([])
    required_fields = (
        "title", "description", "category", "lat", "lng",
        "address", "photo_url", "rating", "price_level",
        "types", "opening_hours",
    )
    for item in items:
        for field in required_fields:
            assert field in item, f"Missing field '{field}' in item '{item.get('title')}'"


async def test_plan_trip_returns_fallback():
    result = await llm_client.plan_trip("5-day Thailand")
    assert result["trip_name"] == "Thailand Getaway"
    assert result["duration_days"] == 3
    assert result["start_date"] is None
    assert len(result["items"]) == len(_BANGKOK_FALLBACK_ITEMS)


async def test_plan_trip_items_are_fresh_copies():
    """Mutating returned items must not corrupt the module-level fallback."""
    result = await llm_client.plan_trip("test")
    original_title = _BANGKOK_FALLBACK_ITEMS[0]["title"]
    result["items"][0]["title"] = "MUTATED"
    assert _BANGKOK_FALLBACK_ITEMS[0]["title"] == original_title
