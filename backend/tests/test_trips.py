"""
Integration tests for trip endpoints including member management.
Uses SQLite in-memory via conftest.py fixtures.
"""
import pytest
from httpx import AsyncClient


# ── Helpers ────────────────────────────────────────────────────────────────────

async def create_trip(client: AsyncClient, headers: dict, name: str = "Test Trip") -> dict:
    resp = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ── Basic CRUD ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_trip(client, auth_headers):
    resp = await client.post(
        "/api/trips/", json={"name": "Paris Escape"}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Paris Escape"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_trip_unauthenticated(client):
    resp = await client.post("/api/trips/", json={"name": "Ghost Trip"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_my_trips_empty(client, auth_headers):
    resp = await client.get("/api/trips/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_my_trips_returns_owned(client, auth_headers):
    await create_trip(client, auth_headers, "Trip A")
    await create_trip(client, auth_headers, "Trip B")
    resp = await client.get("/api/trips/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_trip_detail(client, auth_headers):
    trip = await create_trip(client, auth_headers, "Tokyo Run")
    resp = await client.get(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Tokyo Run"


@pytest.mark.asyncio
async def test_get_trip_detail_forbidden_for_non_member(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_trip_isolation_between_users(client, auth_headers, second_auth_headers):
    await create_trip(client, auth_headers, "Alice Trip")
    await create_trip(client, second_auth_headers, "Bob Trip")

    alice_trips = (await client.get("/api/trips/", headers=auth_headers)).json()
    bob_trips = (await client.get("/api/trips/", headers=second_auth_headers)).json()

    assert len(alice_trips) == 1
    assert alice_trips[0]["name"] == "Alice Trip"
    assert len(bob_trips) == 1
    assert bob_trips[0]["name"] == "Bob Trip"


# ── Members ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_members_includes_creator(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"
    assert members[0]["user"]["email"] == "alice@test.com"


@pytest.mark.asyncio
async def test_get_members_forbidden_non_member(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}/members", headers=second_auth_headers)
    assert resp.status_code == 403


# ── Invite ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_registered_user(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)

    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "editor"
    assert data["user"]["email"] == "bob@test.com"


@pytest.mark.asyncio
async def test_invite_shows_in_members_list(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    members = (
        await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)
    ).json()
    assert len(members) == 2
    emails = {m["user"]["email"] for m in members}
    assert {"alice@test.com", "bob@test.com"} == emails


@pytest.mark.asyncio
async def test_invite_nonexistent_email_returns_404(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "ghost@nowhere.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invite_duplicate_returns_409(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_invite_by_non_member_forbidden(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "alice@test.com"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invited_member_can_view_trip(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    # Bob can now get the trip details
    resp = await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_invited_member_sees_trip_in_their_list(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers, "Shared Adventure")
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    bob_trips = (await client.get("/api/trips/", headers=second_auth_headers)).json()
    assert any(t["name"] == "Shared Adventure" for t in bob_trips)
