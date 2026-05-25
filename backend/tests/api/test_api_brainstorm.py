"""API tests for brainstorm.py — items, messages, chat, extract, bulk, promote."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import create_trip

NO_AUTH = {"Cookie": "", "Authorization": ""}


def _mock_brainstorm_client():
    """Return a mock brainstorm LLM client."""
    client = MagicMock()
    client.chat = AsyncMock(return_value="Great ideas! Visit the Eiffel Tower, Louvre Museum.")
    client.extract_items = AsyncMock(return_value=[
        {"title": "Eiffel Tower", "category": "sightseeing"},
        {"title": "Louvre Museum", "category": "culture"},
    ])
    return client


def _mock_maps_svc():
    """Return a mock maps service for enrichment."""
    svc = MagicMock()
    summary = MagicMock(status="full", total=2, enriched=2, skipped=0, reason=None)
    svc.enrich_items_with_summary = AsyncMock(return_value=(
        [{"title": "Eiffel Tower", "category": "sightseeing"}, {"title": "Louvre Museum", "category": "culture"}],
        summary,
    ))
    return svc


# ── GET /api/trips/{trip_id}/brainstorm/items ──────────────────────────────

async def test_brainstorm_list_items_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]

    # Test 1a - GET - 200 OK - Empty items initially
    resp = await client.get(f"/api/trips/{tid}/brainstorm/items", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 1b - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/trips/{tid}/brainstorm/items", headers=second_auth_headers)
    assert resp.status_code == 403

    # Test 1c - GET - 401 Unauthorized - No auth
    resp = await client.get(f"/api/trips/{tid}/brainstorm/items", headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/trips/{trip_id}/brainstorm/messages ───────────────────────────

async def test_brainstorm_list_messages_get(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]

    # Test 2a - GET - 200 OK - Empty messages initially
    resp = await client.get(f"/api/trips/{tid}/brainstorm/messages", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ── POST /api/trips/{trip_id}/brainstorm/messages/seed ─────────────────────

async def test_brainstorm_seed_messages_post(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]

    # Test 3a - POST - 200 OK - Seed messages
    resp = await client.post(f"/api/trips/{tid}/brainstorm/messages/seed", headers=auth_headers, json={
        "messages": [
            {"role": "user", "content": "Plan a trip to Paris"},
            {"role": "assistant", "content": "Great choice! Paris has so much."},
        ],
    })
    assert resp.status_code == 200
    assert resp.json()["seeded"] == 2

    # Test 3b - POST - 409 Conflict - Already seeded
    resp = await client.post(f"/api/trips/{tid}/brainstorm/messages/seed", headers=auth_headers, json={
        "messages": [{"role": "user", "content": "Again?"}],
    })
    assert resp.status_code == 409


# ── POST /api/trips/{trip_id}/brainstorm/chat ──────────────────────────────

async def test_brainstorm_chat_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]

    # Test 4a - POST - 200 OK - Chat with LLM mock
    with patch("app.api.endpoints.brainstorm.get_brainstorm_client", return_value=_mock_brainstorm_client()):
        resp = await client.post(f"/api/trips/{tid}/brainstorm/chat", headers=auth_headers, json={
            "message": "What should I see in Paris?",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "assistant_message" in data
        assert "history" in data

    # Test 4b - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/trips/{tid}/brainstorm/chat", headers=second_auth_headers, json={
        "message": "Hack attempt",
    })
    assert resp.status_code == 403

    # Test 4c - POST - 422 Unprocessable Entity - Missing message field
    resp = await client.post(f"/api/trips/{tid}/brainstorm/chat", headers=auth_headers, json={})
    assert resp.status_code == 422


# ── POST /api/trips/{trip_id}/brainstorm/extract ───────────────────────────

async def test_brainstorm_extract_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]

    # Test 5a - POST - 200 OK - No messages to extract returns empty
    resp = await client.post(f"/api/trips/{tid}/brainstorm/extract", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    # Test 5b - POST - 200 OK - Extract after chat
    with patch("app.api.endpoints.brainstorm.get_brainstorm_client", return_value=_mock_brainstorm_client()):
        await client.post(f"/api/trips/{tid}/brainstorm/chat", headers=auth_headers, json={
            "message": "Plan activities in Rome",
        })

    with patch("app.api.endpoints.brainstorm.get_brainstorm_client", return_value=_mock_brainstorm_client()):
        resp = await client.post(f"/api/trips/{tid}/brainstorm/extract", headers=auth_headers)
        assert resp.status_code == 200

    # Test 5c - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/trips/{tid}/brainstorm/extract", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/trips/{trip_id}/brainstorm/bulk ──────────────────────────────

async def test_brainstorm_bulk_insert_post(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]

    # Test 6a - POST - 200 OK - Bulk insert items
    resp = await client.post(f"/api/trips/{tid}/brainstorm/bulk", headers=auth_headers, json={
        "items": [
            {"title": "Eiffel Tower", "category": "sightseeing"},
            {"title": "Seine Cruise", "category": "experience"},
        ],
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Test 6b - POST - 200 OK - Empty items list
    resp = await client.post(f"/api/trips/{tid}/brainstorm/bulk", headers=auth_headers, json={
        "items": [],
    })
    assert resp.status_code == 200
    assert resp.json() == []


# ── POST /api/trips/{trip_id}/brainstorm/promote ───────────────────────────

async def test_brainstorm_promote_post(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]

    # Seed brainstorm items first
    await client.post(f"/api/trips/{tid}/brainstorm/bulk", headers=auth_headers, json={
        "items": [{"title": "Museum", "category": "culture"}],
    })

    # Test 7a - POST - 200 OK - Promote all brainstorm items to idea bin
    resp = await client.post(f"/api/trips/{tid}/brainstorm/promote", headers=auth_headers, json={})
    assert resp.status_code == 200
    promoted = resp.json()
    assert len(promoted) >= 1

    # Test 7b - POST - 200 OK - Promote with empty bin returns empty
    resp = await client.post(f"/api/trips/{tid}/brainstorm/promote", headers=auth_headers, json={})
    assert resp.status_code == 200
    assert resp.json() == []


# ── DELETE /api/trips/{trip_id}/brainstorm/items ───────────────────────────

async def test_brainstorm_clear_items_delete(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]
    await client.post(f"/api/trips/{tid}/brainstorm/bulk", headers=auth_headers, json={
        "items": [{"title": "Item 1"}],
    })

    # Test 8a - DELETE - 204 No Content - Clear all items
    resp = await client.delete(f"/api/trips/{tid}/brainstorm/items", headers=auth_headers)
    assert resp.status_code == 204

    # Verify items are gone
    items_resp = await client.get(f"/api/trips/{tid}/brainstorm/items", headers=auth_headers)
    assert items_resp.json() == []


# ── DELETE /api/trips/{trip_id}/brainstorm/items/{item_id} ─────────────────

async def test_brainstorm_delete_item_delete(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    tid = trip["id"]
    bulk_resp = await client.post(f"/api/trips/{tid}/brainstorm/bulk", headers=auth_headers, json={
        "items": [{"title": "Deleteable"}],
    })
    item_id = bulk_resp.json()[0]["id"]

    # Test 9a - DELETE - 204 No Content - Delete specific item
    resp = await client.delete(f"/api/trips/{tid}/brainstorm/items/{item_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Test 9b - DELETE - 404 Not Found - Already deleted
    resp = await client.delete(f"/api/trips/{tid}/brainstorm/items/{item_id}", headers=auth_headers)
    assert resp.status_code == 404
