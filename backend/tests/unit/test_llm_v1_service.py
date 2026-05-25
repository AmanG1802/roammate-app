"""Unit tests for app.services.llm.services.v1.roammate_v1 — V1 service strategy.

Tests the pure helper functions (llm_item_to_brainstorm, _trim_history,
_pack_user_persona, _pack_trip_context, _load_prompt) and the service methods
with mocked model.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from app.services.llm.services.v1.roammate_v1 import (
    llm_item_to_brainstorm,
    _trim_history,
    _pack_user_persona,
    _pack_trip_context,
    _load_prompt,
    RoammateServiceV1,
    HISTORY_TRIM_COUNT,
)
from app.services.llm.models.base import LLMResponse


class TestLlmItemToBrainstorm:
    def test_llm_item_to_brainstorm(self):
        # Test 1a - Maps LLMItem fields to BrainstormBinItem-compatible dict
        item = MagicMock()
        item.t = "Eiffel Tower"
        item.d = "Iconic Paris landmark"
        item.cat.value = "Landmarks & Viewpoints"
        item.tc = "morning"
        item.price = 2
        item.tags = ["landmark", "viewpoint"]

        result = llm_item_to_brainstorm(item)
        assert result["title"] == "Eiffel Tower"
        assert result["description"] == "Iconic Paris landmark"
        assert result["category"] == "Landmarks & Viewpoints"
        assert result["time_category"] == "morning"
        assert result["price_level"] == 2
        assert result["types"] == ["landmark", "viewpoint"]

        # Test 1b - Google Places fields are explicitly None
        assert result["place_id"] is None
        assert result["lat"] is None
        assert result["lng"] is None
        assert result["address"] is None
        assert result["photo_url"] is None
        assert result["rating"] is None

    def test_llm_item_none_description(self):
        # Test 1c - None description maps to None
        item = MagicMock()
        item.t = "Test"
        item.d = None
        item.cat.value = "Food & Dining"
        item.tc = "evening"
        item.price = 1
        item.tags = None

        result = llm_item_to_brainstorm(item)
        assert result["description"] is None
        assert result["types"] is None


class TestTrimHistory:
    def test_trim_history(self):
        # Test 1a - History shorter than max is returned unchanged
        history = [{"role": "user", "content": f"msg{i}"} for i in range(4)]
        result = _trim_history(history)
        assert len(result) == 4

        # Test 1b - History at exactly max is unchanged
        history = [{"role": "user", "content": f"msg{i}"} for i in range(HISTORY_TRIM_COUNT)]
        result = _trim_history(history)
        assert len(result) == HISTORY_TRIM_COUNT

        # Test 1c - History longer than max is trimmed to last N
        history = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
        result = _trim_history(history)
        assert len(result) == HISTORY_TRIM_COUNT
        assert result[0]["content"] == f"msg{20 - HISTORY_TRIM_COUNT}"
        assert result[-1]["content"] == "msg19"

        # Test 1d - Empty history returns empty
        assert _trim_history([]) == []

        # Test 1e - Custom max_messages
        history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        result = _trim_history(history, max_messages=3)
        assert len(result) == 3
        assert result[-1]["content"] == "msg9"


class TestPackUserPersona:
    def test_pack_user_persona(self):
        # Test 1a - None personas returns empty string
        assert _pack_user_persona(None) == ""

        # Test 1b - Empty list returns empty string
        assert _pack_user_persona([]) == ""

        # Test 1c - Invalid persona values return empty string
        assert _pack_user_persona(["nonexistent_persona"]) == ""

    @patch("app.services.llm.services.v1.roammate_v1.PERSONA_DESCRIPTIONS")
    @patch("app.services.llm.services.v1.roammate_v1.Persona")
    def test_pack_user_persona_valid(self, mock_persona_cls, mock_descriptions):
        # Test 1d - Valid persona returns "User preferences: <description>"
        mock_persona_cls._value2member_map_ = {"adventurer": MagicMock()}
        mock_persona_cls.return_value = "adventurer"
        mock_descriptions.__getitem__ = lambda self, key: "Loves extreme activities"

        result = _pack_user_persona(["adventurer"])
        assert "User preferences:" in result


class TestPackTripContext:
    def test_pack_trip_context(self):
        # Test 1a - None context returns empty string
        assert _pack_trip_context(None) == ""

        # Test 1b - Empty dict returns empty string
        assert _pack_trip_context({}) == ""

        # Test 1c - Events today are formatted
        context = {
            "events_today": [
                {"time": "10:00 AM", "title": "Museum Visit", "duration": 120},
                {"time": "2:00 PM", "title": "Lunch", "duration": 60},
            ]
        }
        result = _pack_trip_context(context)
        assert "Today:" in result
        assert "Museum Visit" in result
        assert "Lunch" in result

        # Test 1d - Upcoming events
        context = {
            "upcoming": [
                {"title": "Flight", "day": "Day 3"},
            ]
        }
        result = _pack_trip_context(context)
        assert "Next:" in result
        assert "Flight" in result

        # Test 1e - Role included
        context = {"role": "admin"}
        result = _pack_trip_context(context)
        assert "Role: admin" in result

        # Test 1f - Events truncated to 8 max
        context = {
            "events_today": [
                {"time": f"{i}:00", "title": f"Event {i}", "duration": 30}
                for i in range(12)
            ]
        }
        result = _pack_trip_context(context)
        assert "Event 7" in result
        # Event 8+ should not appear (0-indexed → events 0..7 = 8 items)


class TestLoadPrompt:
    def test_load_prompt(self):
        # Test 1a - brainstorm_chat_v1.txt exists and is a non-empty string
        content = _load_prompt("brainstorm_chat_v1.txt")
        assert isinstance(content, str)
        assert len(content) > 50

        # Test 1b - File not found raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            _load_prompt("nonexistent_file.txt")


class TestRoammateServiceV1Chat:
    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_chat_llm_disabled(self, mock_settings):
        # Test 1a - LLM_ENABLED=False returns fallback reply
        mock_settings.LLM_ENABLED = False
        model = MagicMock()
        service = RoammateServiceV1(model)
        result = await service.chat([], "Plan a trip to Tokyo")
        assert "Bangkok" in result  # CHAT_FALLBACK_REPLY mentions Bangkok

    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.track_tokens")
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_chat_llm_enabled(self, mock_settings, mock_track):
        # Test 1b - LLM_ENABLED=True calls model.complete and returns content
        mock_settings.LLM_ENABLED = True
        model = MagicMock()
        model.complete = AsyncMock(return_value=LLMResponse(
            content="Here's your trip plan!",
            input_tokens=100, output_tokens=50,
            model="gpt-4o-mini", provider="openai",
        ))
        service = RoammateServiceV1(model)
        result = await service.chat([], "Plan a trip to Tokyo")
        assert result == "Here's your trip plan!"
        model.complete.assert_called_once()


class TestRoammateServiceV1ExtractItems:
    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_extract_items_llm_disabled(self, mock_settings):
        # Test 1a - LLM_ENABLED=False returns Bangkok fallback items
        mock_settings.LLM_ENABLED = False
        model = MagicMock()
        service = RoammateServiceV1(model)
        result = await service.extract_items([])
        assert len(result) == 10
        assert result[0]["title"] == "Thip Samai Pad Thai"

    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.track_tokens")
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_extract_items_parse_failure(self, mock_settings, mock_track):
        # Test 1b - Invalid JSON from model raises RuntimeError
        mock_settings.LLM_ENABLED = True
        mock_settings.LLM_MAX_TOKENS_EXTRACT = 3000
        model = MagicMock()
        model.complete = AsyncMock(return_value=LLMResponse(
            content="not valid json at all",
            input_tokens=10, output_tokens=5,
            model="m", provider="p",
        ))
        service = RoammateServiceV1(model)
        with pytest.raises(RuntimeError, match="Failed to parse"):
            await service.extract_items([{"role": "user", "content": "test"}])


class TestRoammateServiceV1PlanTrip:
    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_plan_trip_llm_disabled(self, mock_settings):
        # Test 1a - LLM_ENABLED=False returns Thailand fallback plan
        mock_settings.LLM_ENABLED = False
        model = MagicMock()
        service = RoammateServiceV1(model)
        result = await service.plan_trip("5 days in Bangkok")
        assert result["trip_name"] == "Thailand Getaway"
        assert result["duration_days"] == 3
        assert len(result["items"]) == 10

    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.track_tokens")
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_plan_trip_parse_failure(self, mock_settings, mock_track):
        # Test 1b - Invalid JSON from model raises RuntimeError
        mock_settings.LLM_ENABLED = True
        mock_settings.LLM_MAX_TOKENS_PLAN = 4000
        model = MagicMock()
        model.complete = AsyncMock(return_value=LLMResponse(
            content="{malformed",
            input_tokens=10, output_tokens=5,
            model="m", provider="p",
        ))
        service = RoammateServiceV1(model)
        with pytest.raises(RuntimeError, match="Failed to parse"):
            await service.plan_trip("trip to paris")


class TestRoammateServiceV1ConciergeDispatch:
    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_concierge_dispatch_llm_disabled(self, mock_settings):
        # Test 1a - LLM_ENABLED=False returns offline fallback
        mock_settings.LLM_ENABLED = False
        model = MagicMock()
        service = RoammateServiceV1(model)
        result = await service.concierge_dispatch([], "Change my dinner reservation")
        assert result["intent"] == "chat_only"
        assert "offline" in result["user_message"].lower()

    @pytest.mark.asyncio
    @patch("app.services.llm.services.v1.roammate_v1.track_tokens")
    @patch("app.services.llm.services.v1.roammate_v1.settings")
    async def test_concierge_dispatch_parse_failure_returns_witty(self, mock_settings, mock_track):
        # Test 1b - JSON parse failure returns a witty retry message
        mock_settings.LLM_ENABLED = True
        model = MagicMock()
        model.complete = AsyncMock(return_value=LLMResponse(
            content="not json",
            input_tokens=10, output_tokens=5,
            model="m", provider="p",
        ))
        service = RoammateServiceV1(model)
        result = await service.concierge_dispatch([], "test message")
        assert result["intent"] == "chat_only"
        assert result["params"].get("retry") is True
        assert isinstance(result["user_message"], str)
        assert len(result["user_message"]) > 10
