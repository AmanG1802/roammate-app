"""
Tests for /api/events/* endpoints:
  GET  /events/?trip_id=
  POST /events/ripple/{trip_id}
  POST /events/quick-add/{trip_id}
"""
import pytest
from httpx import AsyncClient


async def create_trip(client: AsyncClient, headers: dict, name: str = "Test Trip") -> dict:
    resp = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# GET /events/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_events_unauthenticated(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/events/?trip_id={trip['id']}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_events_missing_trip_id(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/events/", headers=auth_headers)
    assert resp.status_code == 422  # trip_id is required


@pytest.mark.asyncio
async def test_get_events_empty(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_events_forbidden_for_non_member(
    client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/events/?trip_id={trip['id']}", headers=second_auth_headers
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /events/ripple/{trip_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ripple_unauthenticated(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 30, "start_from_time": "2026-07-01T10:00:00"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ripple_forbidden_for_non_member(
    client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 30, "start_from_time": "2026-07-01T10:00:00"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ripple_empty_itinerary(client: AsyncClient, auth_headers: dict):
    """Ripple on an empty trip returns an empty list."""
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 30, "start_from_time": "2026-07-01T10:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Health check (sanity)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
