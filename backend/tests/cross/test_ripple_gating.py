"""Ripple Engine access gating — only trip admins may fire it."""
import pytest


async def create_trip(client, headers, name="Trip"):
    r = await client.post("/api/trips/", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def invite_and_accept(client, admin_headers, invitee_headers, trip_id, email, role):
    r = await client.post(
        f"/api/trips/{trip_id}/invite",
        json={"email": email, "role": role},
        headers=admin_headers,
    )
    mid = r.json()["id"]
    r2 = await client.post(f"/api/trips/invitations/{mid}/accept", headers=invitee_headers)
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_fire_ripple(client, auth_headers):
    trip = await create_trip(client, auth_headers)
    r = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 15},
        headers=auth_headers,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["view_only", "view_with_vote"])
async def test_non_admin_cannot_fire_ripple(
    client, auth_headers, second_auth_headers, role
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", role
    )
    r = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 15},
        headers=second_auth_headers,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_fire_ripple(
    client, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    r = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 15},
        headers=second_auth_headers,
    )
    assert r.status_code == 403
