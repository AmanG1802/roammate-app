"""Unit tests for LLM client surfaces (brainstorm, concierge, dashboard).

Tests context assembly logic — actual LLM calls are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.llm.clients.base import BaseLLMClient
from app.services.llm.clients.brainstorm_client import BrainstormChatClient
from app.services.llm.clients.concierge_client import ConciergeChatClient
from app.services.llm.clients.dashboard_client import DashboardClient


class TestBaseLLMClient:
    def test_base_client_service_property(self):
        # Test 1a - service property returns injected service
        mock_service = MagicMock()
        client = BaseLLMClient(mock_service)
        assert client.service is mock_service


class TestBrainstormChatClient:
    @pytest.mark.asyncio
    async def test_chat_passes_context(self):
        # Test 1a - chat builds correct context with source=brainstorm
        mock_service = MagicMock()
        mock_service.chat = AsyncMock(return_value="response")
        client = BrainstormChatClient(mock_service)

        result = await client.chat(
            [{"role": "user", "content": "hi"}],
            "Plan a trip",
            trip_id=5,
            user_id=42,
            personas=["foodie"],
        )
        assert result == "response"
        call_ctx = mock_service.chat.call_args[1]["context"]
        assert call_ctx["source"] == "brainstorm"
        assert call_ctx["trip_id"] == 5
        assert call_ctx["user_id"] == 42
        assert call_ctx["personas"] == ["foodie"]

    @pytest.mark.asyncio
    async def test_chat_minimal_context(self):
        # Test 1b - Only source included when no optional params
        mock_service = MagicMock()
        mock_service.chat = AsyncMock(return_value="hi")
        client = BrainstormChatClient(mock_service)

        await client.chat([], "hello")
        call_ctx = mock_service.chat.call_args[1]["context"]
        assert call_ctx == {"source": "brainstorm"}

    @pytest.mark.asyncio
    async def test_extract_items_passes_context(self):
        # Test 1c - extract_items includes correct context
        mock_service = MagicMock()
        mock_service.extract_items = AsyncMock(return_value=[{"title": "x"}])
        client = BrainstormChatClient(mock_service)

        result = await client.extract_items([], trip_id=10, user_id=1)
        assert result == [{"title": "x"}]
        call_ctx = mock_service.extract_items.call_args[1]["context"]
        assert call_ctx["source"] == "brainstorm"
        assert call_ctx["trip_id"] == 10


class TestConciergeChatClient:
    @pytest.mark.asyncio
    async def test_chat_passes_trip_context(self):
        # Test 1a - chat merges trip_context into context
        mock_service = MagicMock()
        mock_service.chat = AsyncMock(return_value="concierge reply")
        client = ConciergeChatClient(mock_service)

        trip_ctx = {"events_today": [{"title": "Museum"}], "role": "admin"}
        result = await client.chat([], "What's next?", trip_context=trip_ctx, user_id=7)
        assert result == "concierge reply"
        call_ctx = mock_service.chat.call_args[1]["context"]
        assert call_ctx["source"] == "concierge"
        assert call_ctx["user_id"] == 7
        assert call_ctx["events_today"] == [{"title": "Museum"}]
        assert call_ctx["role"] == "admin"

    @pytest.mark.asyncio
    async def test_dispatch_passes_context(self):
        # Test 1b - dispatch delegates to concierge_dispatch
        mock_service = MagicMock()
        mock_service.concierge_dispatch = AsyncMock(return_value={"intent": "add_event"})
        client = ConciergeChatClient(mock_service)

        result = await client.dispatch([], "add coffee", user_id=3)
        assert result == {"intent": "add_event"}
        call_ctx = mock_service.concierge_dispatch.call_args[1]["context"]
        assert call_ctx["source"] == "concierge"
        assert call_ctx["user_id"] == 3


class TestDashboardClient:
    @pytest.mark.asyncio
    async def test_plan_trip_passes_context(self):
        # Test 1a - plan_trip builds dashboard context
        mock_service = MagicMock()
        mock_service.plan_trip = AsyncMock(return_value={"trip_name": "Paris Trip"})
        client = DashboardClient(mock_service)

        result = await client.plan_trip("5 days in Paris", user_id=99)
        assert result == {"trip_name": "Paris Trip"}
        call_ctx = mock_service.plan_trip.call_args[1]["context"]
        assert call_ctx["source"] == "dashboard"
        assert call_ctx["user_id"] == 99

    @pytest.mark.asyncio
    async def test_plan_trip_no_user(self):
        # Test 1b - No user_id means context only has source
        mock_service = MagicMock()
        mock_service.plan_trip = AsyncMock(return_value={})
        client = DashboardClient(mock_service)

        await client.plan_trip("quick trip")
        call_ctx = mock_service.plan_trip.call_args[1]["context"]
        assert call_ctx == {"source": "dashboard"}
