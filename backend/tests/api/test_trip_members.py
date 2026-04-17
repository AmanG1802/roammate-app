"""Tests for trip member management and invitations."""
from httpx import AsyncClient
from tests.conftest import create_trip, invite_and_accept


# ── Invite ────────────────────────────────────────────────────────────────────

async def test_admin_can_invite(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "invited"
    assert data["role"] == "view_only"
    assert data["user"]["email"] == "bob@test.com"


async def test_non_admin_cannot_invite(
    client: AsyncClient, auth_headers, second_auth_headers, third_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "carol@test.com", "role": "view_only"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_non_member_cannot_invite(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "x@y.com", "role": "view_only"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_invite_unknown_email(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "ghost@nobody.com", "role": "view_only"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_invite_already_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com"
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


async def test_invite_already_invited(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


async def test_invite_invalid_role(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "superuser"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_invite_default_role_view_only(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "view_only"


# ── Pending invitations ───────────────────────────────────────────────────────

async def test_pending_invitations(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers, name="Trip A")
    await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    resp = await client.get(
        "/api/trips/invitations/pending", headers=second_auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trip"]["name"] == "Trip A"
    assert data[0]["inviter"]["email"] == "alice@test.com"


async def test_pending_empty(client: AsyncClient, second_auth_headers):
    resp = await client.get(
        "/api/trips/invitations/pending", headers=second_auth_headers
    )
    assert resp.json() == []


# ── Accept / decline ──────────────────────────────────────────────────────────

async def test_accept_invitation(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    invite_resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    member_id = invite_resp.json()["id"]
    resp = await client.post(
        f"/api/trips/invitations/{member_id}/accept", headers=second_auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


async def test_accept_nonexistent_invitation(client: AsyncClient, second_auth_headers):
    resp = await client.post(
        "/api/trips/invitations/9999/accept", headers=second_auth_headers
    )
    assert resp.status_code == 404


async def test_accept_foreign_invitation(
    client: AsyncClient, auth_headers, second_auth_headers, third_auth_headers
):
    trip = await create_trip(client, auth_headers)
    invite_resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    # Carol tries to accept Bob's invitation
    resp = await client.post(
        f"/api/trips/invitations/{invite_resp.json()['id']}/accept",
        headers=third_auth_headers,
    )
    assert resp.status_code == 404


async def test_accept_already_accepted(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    invite_resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    member_id = invite_resp.json()["id"]
    await client.post(
        f"/api/trips/invitations/{member_id}/accept", headers=second_auth_headers
    )
    resp = await client.post(
        f"/api/trips/invitations/{member_id}/accept", headers=second_auth_headers
    )
    assert resp.status_code == 404


async def test_decline_invitation(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    invite_resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "bob@test.com", "role": "view_only"},
        headers=auth_headers,
    )
    member_id = invite_resp.json()["id"]
    resp = await client.delete(
        f"/api/trips/invitations/{member_id}/decline", headers=second_auth_headers
    )
    assert resp.status_code == 204
    # no longer pending
    pending = (
        await client.get(
            "/api/trips/invitations/pending", headers=second_auth_headers
        )
    ).json()
    assert pending == []


# ── Members ───────────────────────────────────────────────────────────────────

async def test_get_members_by_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com"
    )
    resp = await client.get(
        f"/api/trips/{trip['id']}/members", headers=second_auth_headers
    )
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 2


async def test_get_members_by_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/trips/{trip['id']}/members", headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_update_member_role(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    member = await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    resp = await client.patch(
        f"/api/trips/{trip['id']}/members/{member['id']}/role",
        json={"role": "admin"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_update_role_by_non_admin(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    member = await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    resp = await client.patch(
        f"/api/trips/{trip['id']}/members/{member['id']}/role",
        json={"role": "admin"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_update_role_invalid(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    member = await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com"
    )
    resp = await client.patch(
        f"/api/trips/{trip['id']}/members/{member['id']}/role",
        json={"role": "nope"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_remove_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    member = await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com"
    )
    resp = await client.delete(
        f"/api/trips/{trip['id']}/members/{member['id']}", headers=auth_headers
    )
    assert resp.status_code == 204
    # Bob can no longer read the trip
    resp = await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_admin_cannot_remove_self(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    members = (
        await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)
    ).json()
    own = [m for m in members if m["user"]["email"] == "alice@test.com"][0]
    resp = await client.delete(
        f"/api/trips/{trip['id']}/members/{own['id']}", headers=auth_headers
    )
    assert resp.status_code == 400


async def test_remove_by_non_admin(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    members = (
        await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)
    ).json()
    alice = [m for m in members if m["user"]["email"] == "alice@test.com"][0]
    resp = await client.delete(
        f"/api/trips/{trip['id']}/members/{alice['id']}", headers=second_auth_headers
    )
    assert resp.status_code == 403


async def test_remove_nonexistent_member(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.delete(
        f"/api/trips/{trip['id']}/members/9999", headers=auth_headers
    )
    assert resp.status_code == 404
