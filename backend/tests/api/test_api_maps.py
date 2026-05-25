"""API tests for maps.py — compute route, get stored route, save client route, re-enrich."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from tests.conftest import create_trip, invite_and_accept

NO_AUTH = {"Cookie": "", "Authorization": ""}


# ── POST /api/trips/{trip_id}/route ────────────────────────────────────────

async def test_compute_route_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Route Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 1a - POST - 200 OK - No events returns reason=need_two_points
    resp = await client.post(f"/api/trips/{tid}/route", headers=auth_headers, json={
        "day_date": "2025-06-01",
    })
    assert resp.status_code == 200
    assert resp.json().get("reason") == "need_two_points"

    # Test 1b - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/trips/{tid}/route", headers=second_auth_headers, json={
        "day_date": "2025-06-01",
    })
    assert resp.status_code == 403

    # Test 1c - POST - 401 Unauthorized - No auth
    resp = await client.post(f"/api/trips/{tid}/route", json={"day_date": "2025-06-01"}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/trips/{trip_id}/route ─────────────────────────────────────────

async def test_get_stored_route_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Route Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 2a - GET - 200 OK - No stored route returns null
    resp = await client.get(f"/api/trips/{tid}/route?day_date=2025-06-01", headers=auth_headers)
    assert resp.status_code == 200

    # Test 2b - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/trips/{tid}/route?day_date=2025-06-01", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/trips/{trip_id}/route/save ───────────────────────────────────

async def test_save_client_route_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Route Trip", start_date="2025-06-01T00:00:00")
    tid = trip["id"]

    # Test 3a - POST - 200 OK - Save client-computed route
    resp = await client.post(f"/api/trips/{tid}/route/save", headers=auth_headers, json={
        "day_date": "2025-06-01",
        "total_duration_s": 1200,
        "total_distance_m": 5000,
        "ordered_event_ids": [],
    })
    assert resp.status_code == 200

    # Test 3b - POST - 403 Forbidden - Non-member
    resp = await client.post(f"/api/trips/{tid}/route/save", headers=second_auth_headers, json={
        "day_date": "2025-06-01",
    })
    assert resp.status_code == 403


# ── POST /api/trips/enrich ────────────────────────────────────────────────

async def test_re_enrich_item_post(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Enrich Trip")
    tid = trip["id"]

    # Ingest to get an idea item
    resp = await client.post(f"/api/trips/{tid}/ingest", headers=auth_headers, json={
        "text": "Visit the Colosseum",
    })
    ideas = resp.json()

    if ideas:
        idea_id = ideas[0]["id"]

        # Test 4a - POST - 422 Unprocessable Entity - Enrichment fails (mocked)
        mock_svc = MagicMock()
        mock_svc.enrich_item = AsyncMock(return_value={"place_id": None})
        with patch("app.api.endpoints.maps.get_enrichment_service", return_value=mock_svc):
            resp = await client.post("/api/trips/enrich", headers=auth_headers, json={
                "kind": "idea", "item_id": idea_id,
            })
            assert resp.status_code == 422

    # Test 4b - POST - 404 Not Found - Non-existent item
    resp = await client.post("/api/trips/enrich", headers=auth_headers, json={
        "kind": "idea", "item_id": 999999,
    })
    assert resp.status_code == 404

    # Test 4c - POST - 422 Unprocessable Entity - Invalid kind
    resp = await client.post("/api/trips/enrich", headers=auth_headers, json={
        "kind": "invalid", "item_id": 1,
    })
    assert resp.status_code == 422

    # Test 4d - POST - 401 Unauthorized - No auth
    resp = await client.post("/api/trips/enrich", json={"kind": "idea", "item_id": 1}, headers=NO_AUTH)
    assert resp.status_code == 401
