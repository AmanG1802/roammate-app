"""API tests for concierge.py — chat, execute, find-nearby, skip-event, whats-next, today-summary."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import create_trip, invite_and_accept

NO_AUTH = {"Cookie": "", "Authorization": ""}
_ENTITLEMENT_PATCH = "app.api.endpoints.concierge.entitlements.enforce_concierge"


def _mock_concierge_client():
    client = MagicMock()
    client.dispatch = AsyncMock(return_value={
        "intent": "chat_only",
        "user_message": "Here's your itinerary info.",
        "params": {},
        "requires_confirmation": False,
    })
    return client


def _mock_executor():
    executor = MagicMock()
    executor.execute = AsyncMock(return_value={
        "success": True,
        "message": "Event skipped successfully.",
        "updated_events": [],
    })
    return executor


# ── POST /api/concierge/{trip_id}/chat ─────────────────────────────────────

async def test_concierge_chat_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Concierge Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 1a - POST - 200 OK - Chat with LLM mock
    with patch("app.api.endpoints.concierge.get_concierge_client", return_value=_mock_concierge_client()), \
         patch(_ENTITLEMENT_PATCH, new_callable=AsyncMock):
        resp = await client.post(f"/api/concierge/{tid}/chat", headers=auth_headers, json={
            "message": "What's the plan for today?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "intent" in data
        assert "user_message" in data

    # Test 1b - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/concierge/{tid}/chat", headers=second_auth_headers, json={
        "message": "Hack",
    })
    assert resp.status_code == 403

    # Test 1c - POST - 422 Unprocessable Entity - Missing message field
    resp = await client.post(f"/api/concierge/{tid}/chat", headers=auth_headers, json={})
    assert resp.status_code == 422

    # Test 1d - POST - 401 Unauthorized - No auth
    resp = await client.post(f"/api/concierge/{tid}/chat", json={"message": "x"}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/concierge/{trip_id}/execute ──────────────────────────────────

async def test_concierge_execute_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Concierge Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 2a - POST - 200 OK - Execute action
    with patch("app.api.endpoints.concierge.concierge_executor", _mock_executor()), \
         patch(_ENTITLEMENT_PATCH, new_callable=AsyncMock):
        resp = await client.post(f"/api/concierge/{tid}/execute", headers=auth_headers, json={
            "intent": "skip_event", "params": {"event_id": 1},
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    # Test 2b - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/concierge/{tid}/execute", headers=second_auth_headers, json={
        "intent": "skip_event", "params": {"event_id": 1},
    })
    assert resp.status_code == 403


# ── POST /api/concierge/{trip_id}/find-nearby ──────────────────────────────

async def test_find_nearby_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Concierge Trip")
    tid = trip["id"]

    # Test 3a - POST - 200 OK - Find nearby places (mocked)
    mock_maps = MagicMock()
    mock_maps.nearby_search = AsyncMock(return_value=[])
    mock_maps._current_user_id = None
    mock_maps._current_trip_id = None
    with patch("app.api.endpoints.concierge.get_google_maps_service", return_value=mock_maps), \
         patch(_ENTITLEMENT_PATCH, new_callable=AsyncMock):
        resp = await client.post(f"/api/concierge/{tid}/find-nearby", headers=auth_headers, json={
            "query": "coffee shop", "lat": 48.8584, "lng": 2.2945,
        })
        assert resp.status_code == 200
        assert "places" in resp.json()

    # Test 3b - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/concierge/{tid}/find-nearby", headers=second_auth_headers, json={
        "query": "cafe", "lat": 0, "lng": 0,
    })
    assert resp.status_code == 403


# ── POST /api/concierge/{trip_id}/skip-event ───────────────────────────────

async def test_skip_event_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Concierge Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 4a - POST - 200 OK - Skip event (mocked executor)
    with patch("app.api.endpoints.concierge.concierge_executor", _mock_executor()), \
         patch(_ENTITLEMENT_PATCH, new_callable=AsyncMock):
        resp = await client.post(f"/api/concierge/{tid}/skip-event", headers=auth_headers, json={
            "event_id": 1,
        })
        assert resp.status_code == 200

    # Test 4b - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/concierge/{tid}/skip-event", headers=second_auth_headers, json={
        "event_id": 1,
    })
    assert resp.status_code == 403


# ── GET /api/concierge/{trip_id}/whats-next ────────────────────────────────

async def test_whats_next_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Concierge Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 5a - GET - 200 OK - Returns whats-next data (may be null events)
    resp = await client.get(f"/api/concierge/{tid}/whats-next", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "current_event" in data
    assert "next_event" in data

    # Test 5b - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/concierge/{tid}/whats-next", headers=second_auth_headers)
    assert resp.status_code == 403

    # Test 5c - GET - 401 Unauthorized - No auth
    resp = await client.get(f"/api/concierge/{tid}/whats-next", headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/concierge/{trip_id}/today-summary ─────────────────────────────

async def test_today_summary_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Concierge Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 6a - GET - 200 OK - Returns today summary
    resp = await client.get(f"/api/concierge/{tid}/today-summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "completed" in data
    assert "upcoming" in data

    # Test 6b - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/concierge/{tid}/today-summary", headers=second_auth_headers)
    assert resp.status_code == 403
