"""API tests for events.py — timeline event CRUD, move-to-bin, ripple engine."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from tests.conftest import create_trip, invite_and_accept

NO_AUTH = {"Cookie": "", "Authorization": ""}


async def _create_event(client, headers, trip_id, **kwargs):
    payload = {
        "trip_id": trip_id,
        "title": kwargs.get("title", "Test Event"),
        "day_date": kwargs.get("day_date", "2025-06-01"),
        "start_time": kwargs.get("start_time", "10:00:00"),
        "end_time": kwargs.get("end_time", "11:00:00"),
    }
    payload.update({k: v for k, v in kwargs.items() if k not in payload})
    resp = await client.post("/api/events", json=payload, headers=headers)
    return resp


# ── GET /api/events?trip_id= ───────────────────────────────────────────────

async def test_get_events_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Ev Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]

    # Test 1a - GET - 200 OK - Empty events list
    resp = await client.get(f"/api/events?trip_id={trip_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 1b - GET - 200 OK - Returns events after creation
    await _create_event(client, auth_headers, trip_id)
    resp = await client.get(f"/api/events?trip_id={trip_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Test 1c - GET - 403 Forbidden - Non-member access
    resp = await client.get(f"/api/events?trip_id={trip_id}", headers=second_auth_headers)
    assert resp.status_code == 403

    # Test 1d - GET - 401 Unauthorized - No auth
    resp = await client.get(f"/api/events?trip_id={trip_id}", headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/events ──────────────────────────────────────────────────────

async def test_create_event_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Ev Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]

    # Test 2a - POST - 201 Created - Create event with valid payload
    resp = await _create_event(client, auth_headers, trip_id, title="Museum Visit")
    assert resp.status_code == 201
    assert resp.json()["title"] == "Museum Visit"

    # Test 2b - POST - 403 Forbidden - Non-member cannot create event
    resp = await _create_event(client, second_auth_headers, trip_id)
    assert resp.status_code == 403

    # Test 2c - POST - 422 Unprocessable Entity - Missing required fields
    resp = await client.post("/api/events", json={}, headers=auth_headers)
    assert resp.status_code == 422

    # Test 2d - POST - 401 Unauthorized - No auth
    resp = await client.post("/api/events", json={"trip_id": trip_id, "title": "Hack"}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── PATCH /api/events/{event_id} ──────────────────────────────────────────

async def test_update_event_patch(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Ev Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]
    ev_resp = await _create_event(client, auth_headers, trip_id)
    event_id = ev_resp.json()["id"]

    # Test 3a - PATCH - 200 OK - Update event title
    resp = await client.patch(f"/api/events/{event_id}", headers=auth_headers, json={"title": "Updated Title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"

    # Test 3b - PATCH - 200 OK - Update start_time
    resp = await client.patch(f"/api/events/{event_id}", headers=auth_headers, json={"start_time": "09:00:00"})
    assert resp.status_code == 200

    # Test 3c - PATCH - 403 Forbidden - Non-member cannot update
    resp = await client.patch(f"/api/events/{event_id}", headers=second_auth_headers, json={"title": "Hacked"})
    assert resp.status_code == 403

    # Test 3d - PATCH - 404 Not Found - Invalid event_id
    resp = await client.patch("/api/events/999999", headers=auth_headers, json={"title": "Ghost"})
    assert resp.status_code == 404


# ── DELETE /api/events/{event_id} ─────────────────────────────────────────

async def test_delete_event_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Ev Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]
    ev_resp = await _create_event(client, auth_headers, trip_id)
    event_id = ev_resp.json()["id"]

    # Test 4a - DELETE - 204 No Content - Delete event
    resp = await client.delete(f"/api/events/{event_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Test 4b - DELETE - 404 Not Found - Already deleted
    resp = await client.delete(f"/api/events/{event_id}", headers=auth_headers)
    assert resp.status_code == 404

    # Test 4c - DELETE - 403 Forbidden - Non-member cannot delete
    ev2_resp = await _create_event(client, auth_headers, trip_id, title="Event 2")
    ev2_id = ev2_resp.json()["id"]
    resp = await client.delete(f"/api/events/{ev2_id}", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/events/{event_id}/move-to-bin ────────────────────────────────

async def test_move_event_to_bin_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Ev Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]
    ev_resp = await _create_event(client, auth_headers, trip_id, title="Moveable Event")
    event_id = ev_resp.json()["id"]

    # Test 5a - POST - 200 OK - Move event to idea bin
    resp = await client.post(f"/api/events/{event_id}/move-to-bin", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Moveable Event"

    # Test 5b - POST - 404 Not Found - Event already moved/deleted
    resp = await client.post(f"/api/events/{event_id}/move-to-bin", headers=auth_headers)
    assert resp.status_code == 404

    # Test 5c - POST - 403 Forbidden - Non-member cannot move event
    ev3_resp = await _create_event(client, auth_headers, trip_id, title="Another")
    ev3_id = ev3_resp.json()["id"]
    resp = await client.post(f"/api/events/{ev3_id}/move-to-bin", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/events/ripple/{trip_id} ──────────────────────────────────────

async def test_trigger_ripple_engine_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Ev Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]
    await _create_event(client, auth_headers, trip_id, title="E1", start_time="10:00:00", end_time="11:00:00")
    await _create_event(client, auth_headers, trip_id, title="E2", start_time="11:30:00", end_time="12:30:00")

    # Test 6a - POST - 200 OK - Ripple shifts events (start_from_time=None shifts all)
    resp = await client.post(f"/api/events/ripple/{trip_id}", headers=auth_headers, json={
        "delta_minutes": 15,
    })
    assert resp.status_code == 200

    # Test 6b - POST - 403 Forbidden - Non-admin cannot fire ripple
    await invite_and_accept(client, auth_headers, second_auth_headers, trip_id, "bob@test.com", "view_only")
    resp = await client.post(f"/api/events/ripple/{trip_id}", headers=second_auth_headers, json={
        "delta_minutes": 10,
    })
    assert resp.status_code == 403

    # Test 6c - POST - 401 Unauthorized - No auth
    resp = await client.post(f"/api/events/ripple/{trip_id}", json={
        "delta_minutes": 10,
    }, headers=NO_AUTH)
    assert resp.status_code == 401
