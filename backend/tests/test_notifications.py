"""Integration tests for notification fan-out, listing, and read-state."""
import pytest
from httpx import AsyncClient


async def create_trip(client: AsyncClient, headers: dict, name: str = "Trip") -> dict:
    resp = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_unread_count_starts_zero(client, auth_headers):
    resp = await client.get("/api/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"unread": 0}


@pytest.mark.asyncio
async def test_trip_create_emits_self_notification(client, auth_headers):
    await create_trip(client, auth_headers, "Solo Trip")
    resp = await client.get("/api/notifications/", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert any(n["type"] == "trip_created" for n in items)


@pytest.mark.asyncio
async def test_invite_creates_notification_for_invitee(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers, "Shared Trip")
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    bob_inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    invite_notes = [n for n in bob_inbox if n["type"] == "invite_received"]
    assert len(invite_notes) == 1
    assert invite_notes[0]["payload"].get("trip_name") == "Shared Trip"
    assert invite_notes[0]["read_at"] is None

    count = (await client.get("/api/notifications/unread-count", headers=second_auth_headers)).json()
    assert count["unread"] >= 1


@pytest.mark.asyncio
async def test_mark_read_decrements_unread(client, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers, "Trip X")
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )

    inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    assert len(inbox) >= 1
    before = (await client.get("/api/notifications/unread-count", headers=second_auth_headers)).json()["unread"]

    target = inbox[0]["id"]
    r = await client.post(f"/api/notifications/{target}/read", headers=second_auth_headers)
    assert r.status_code in (200, 204)

    after = (await client.get("/api/notifications/unread-count", headers=second_auth_headers)).json()["unread"]
    assert after == before - 1


@pytest.mark.asyncio
async def test_mark_all_read_zeros_unread(client, auth_headers):
    await create_trip(client, auth_headers, "T1")
    await create_trip(client, auth_headers, "T2")

    before = (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["unread"]
    assert before >= 2

    r = await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    assert r.status_code in (200, 204)

    after = (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["unread"]
    assert after == 0


@pytest.mark.asyncio
async def test_notifications_isolated_between_users(
    client, auth_headers, second_auth_headers
):
    """Bob should not see Alice's self-only trip_created notification."""
    await create_trip(client, auth_headers, "Alice Only")

    bob_inbox = (await client.get("/api/notifications/", headers=second_auth_headers)).json()
    assert all(n["type"] != "trip_created" for n in bob_inbox)
