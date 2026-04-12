"""
Tests for /api/trips/* endpoints:
  GET    /trips/
  POST   /trips/
  GET    /trips/{id}
  GET    /trips/{id}/ideas
  POST   /trips/{id}/ingest
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_trip(client: AsyncClient, headers: dict, name: str = "Test Trip") -> dict:
    resp = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_trips_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/trips/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_trip_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/trips/", json={"name": "Sneaky"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Trip CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_trip_success(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/trips/",
        json={"name": "Tokyo Adventure"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Tokyo Adventure"
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_trip_with_dates(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/trips/",
        json={
            "name": "Paris Trip",
            "start_date": "2026-07-01T00:00:00",
            "end_date": "2026-07-10T00:00:00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Paris Trip"
    assert body["start_date"] is not None


@pytest.mark.asyncio
async def test_get_my_trips_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/trips/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_my_trips_returns_own_trips(client: AsyncClient, auth_headers: dict):
    await create_trip(client, auth_headers, "Trip A")
    await create_trip(client, auth_headers, "Trip B")

    resp = await client.get("/api/trips/", headers=auth_headers)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "Trip A" in names
    assert "Trip B" in names


@pytest.mark.asyncio
async def test_get_trips_isolation(
    client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
):
    """User A's trips must not appear in User B's list."""
    await create_trip(client, auth_headers, "Private Trip")

    resp = await client.get("/api/trips/", headers=second_auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_trip_by_id(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers, "Solo Trip")
    trip_id = trip["id"]

    resp = await client.get(f"/api/trips/{trip_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == trip_id


@pytest.mark.asyncio
async def test_get_trip_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/trips/99999", headers=auth_headers)
    assert resp.status_code in [403, 404]  # 403 membership check fires first


@pytest.mark.asyncio
async def test_get_trip_forbidden_for_non_member(
    client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
):
    trip = await create_trip(client, auth_headers, "Exclusive Trip")
    resp = await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Idea Bin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_ideas_empty(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_ideas_forbidden_for_non_member(
    client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=second_auth_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ingest_unauthenticated(client: AsyncClient, auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/ingest",
        json={"text": "Colosseum"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_forbidden_for_non_member(
    client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/ingest",
        json={"text": "Colosseum"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403
