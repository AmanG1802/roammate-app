"""§4 Trip Members & Invitations — invite, accept, decline, role changes, removal."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def test_invite_user_creates_pending_member(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com", "role": "view_only"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "invited"


async def test_invite_duplicate_idempotent(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    r1 = await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    r2 = await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code in (200, 201, 409)


async def test_accept_invitation_sets_accepted(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    mid = resp.json()["id"]
    resp = await client.post(f"/api/trips/invitations/{mid}/accept", headers=second_auth_headers)
    assert resp.status_code == 200


async def test_accept_already_accepted_404(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    members = (await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)).json()
    bob = [m for m in members if m["user"]["email"] == "bob@test.com"][0]
    resp = await client.post(f"/api/trips/invitations/{bob['id']}/accept", headers=second_auth_headers)
    assert resp.status_code in (404, 409, 400)


async def test_accept_foreign_invitation_404(client: AsyncClient, auth_headers, second_auth_headers, third_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    mid = resp.json()["id"]
    resp = await client.post(f"/api/trips/invitations/{mid}/accept", headers=third_auth_headers)
    assert resp.status_code in (403, 404)


async def test_decline_invitation_removes_member(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    mid = resp.json()["id"]
    resp = await client.delete(f"/api/trips/invitations/{mid}/decline", headers=second_auth_headers)
    assert resp.status_code in (200, 204)


async def test_list_pending_invitations(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    resp = await client.get("/api/trips/invitations/pending", headers=second_auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_change_member_role_admin_only(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    members = (await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)).json()
    bob = [m for m in members if m["user"]["email"] == "bob@test.com"][0]
    resp = await client.patch(
        f"/api/trips/{trip['id']}/members/{bob['id']}/role",
        json={"role": "view_with_vote"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_change_member_role_updates_role(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_only")
    members = (await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)).json()
    bob = [m for m in members if m["user"]["email"] == "bob@test.com"][0]
    resp = await client.patch(
        f"/api/trips/{trip['id']}/members/{bob['id']}/role",
        json={"role": "view_with_vote"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_remove_member_admin_only(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    members = (await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)).json()
    bob = [m for m in members if m["user"]["email"] == "bob@test.com"][0]
    resp = await client.delete(f"/api/trips/{trip['id']}/members/{bob['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_remove_member_deletes_row(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    members = (await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)).json()
    bob = [m for m in members if m["user"]["email"] == "bob@test.com"][0]
    resp = await client.delete(f"/api/trips/{trip['id']}/members/{bob['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_list_trip_members(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    resp = await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_non_member_cannot_list_members(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}/members", headers=second_auth_headers)
    assert resp.status_code == 403
