"""API tests for groups.py — group CRUD, members, invitations, trips, idea library."""

import pytest
from httpx import AsyncClient
from tests.conftest import create_trip, invite_and_accept

NO_AUTH = {"Cookie": "", "Authorization": ""}


async def _create_group(client, headers, name="Test Group"):
    resp = await client.post("/api/groups", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def _invite_and_accept_group(client, admin_headers, invitee_headers, group_id, email, role="member"):
    inv_resp = await client.post(f"/api/groups/{group_id}/invite", json={"email": email, "role": role}, headers=admin_headers)
    assert inv_resp.status_code == 201
    member_id = inv_resp.json()["id"]
    acc_resp = await client.post(f"/api/groups/invitations/{member_id}/accept", headers=invitee_headers)
    assert acc_resp.status_code == 200
    return acc_resp.json()


# ── GET /api/groups ────────────────────────────────────────────────────────

async def test_list_my_groups_get(client: AsyncClient, auth_headers: dict):
    # Test 1a - GET - 200 OK - Empty groups initially
    resp = await client.get("/api/groups", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 1b - GET - 200 OK - Returns groups after creation
    await _create_group(client, auth_headers)
    resp = await client.get("/api/groups", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Test 1c - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/groups", headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/groups ───────────────────────────────────────────────────────

async def test_create_group_post(client: AsyncClient, auth_headers: dict):
    # Test 2a - POST - 201 Created - Create group with valid name
    resp = await client.post("/api/groups", json={"name": "Travel Buddies"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Travel Buddies"
    assert resp.json()["my_role"] == "admin"

    # Test 2b - POST - 422 Unprocessable Entity - Empty name
    resp = await client.post("/api/groups", json={"name": "   "}, headers=auth_headers)
    assert resp.status_code == 422

    # Test 2c - POST - 401 Unauthorized - No auth
    resp = await client.post("/api/groups", json={"name": "Hack"}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/groups/{group_id} ─────────────────────────────────────────────

async def test_get_group_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 3a - GET - 200 OK - Member can view group
    resp = await client.get(f"/api/groups/{gid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == gid

    # Test 3b - GET - 403 Forbidden - Non-member cannot view group
    resp = await client.get(f"/api/groups/{gid}", headers=second_auth_headers)
    assert resp.status_code == 403


# ── PATCH /api/groups/{group_id} ───────────────────────────────────────────

async def test_update_group_patch(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 4a - PATCH - 200 OK - Admin renames group
    resp = await client.patch(f"/api/groups/{gid}", headers=auth_headers, json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"

    # Test 4b - PATCH - 403 Forbidden - Non-admin member cannot update
    await _invite_and_accept_group(client, auth_headers, second_auth_headers, gid, "bob@test.com", "member")
    resp = await client.patch(f"/api/groups/{gid}", headers=second_auth_headers, json={"name": "Hacked"})
    assert resp.status_code == 403


# ── DELETE /api/groups/{group_id} ──────────────────────────────────────────

async def test_delete_group_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 5a - DELETE - 403 Forbidden - Non-admin cannot delete
    await _invite_and_accept_group(client, auth_headers, second_auth_headers, gid, "bob@test.com", "member")
    resp = await client.delete(f"/api/groups/{gid}", headers=second_auth_headers)
    assert resp.status_code == 403

    # Test 5b - DELETE - 204 No Content - Admin deletes group
    resp = await client.delete(f"/api/groups/{gid}", headers=auth_headers)
    assert resp.status_code == 204


# ── GET /api/groups/invitations/pending ────────────────────────────────────

async def test_list_my_group_invitations_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 6a - GET - 200 OK - No pending invitations
    resp = await client.get("/api/groups/invitations/pending", headers=second_auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 6b - GET - 200 OK - Returns pending invitation
    await client.post(f"/api/groups/{gid}/invite", json={"email": "bob@test.com", "role": "member"}, headers=auth_headers)
    resp = await client.get("/api/groups/invitations/pending", headers=second_auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── POST /api/groups/invitations/{member_id}/accept ────────────────────────

async def test_accept_group_invitation_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]
    inv_resp = await client.post(f"/api/groups/{gid}/invite", json={"email": "bob@test.com", "role": "member"}, headers=auth_headers)
    member_id = inv_resp.json()["id"]

    # Test 7a - POST - 200 OK - Accept invitation
    resp = await client.post(f"/api/groups/invitations/{member_id}/accept", headers=second_auth_headers)
    assert resp.status_code == 200

    # Test 7b - POST - 404 Not Found - Already accepted
    resp = await client.post(f"/api/groups/invitations/{member_id}/accept", headers=second_auth_headers)
    assert resp.status_code == 404


# ── DELETE /api/groups/invitations/{member_id}/decline ─────────────────────

async def test_decline_group_invitation_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]
    inv_resp = await client.post(f"/api/groups/{gid}/invite", json={"email": "bob@test.com", "role": "member"}, headers=auth_headers)
    member_id = inv_resp.json()["id"]

    # Test 8a - DELETE - 204 No Content - Decline invitation
    resp = await client.delete(f"/api/groups/invitations/{member_id}/decline", headers=second_auth_headers)
    assert resp.status_code == 204


# ── GET /api/groups/{group_id}/members ─────────────────────────────────────

async def test_list_group_members_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 9a - GET - 200 OK - Returns members list
    resp = await client.get(f"/api/groups/{gid}/members", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Test 9b - GET - 403 Forbidden - Non-member cannot list
    resp = await client.get(f"/api/groups/{gid}/members", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/groups/{group_id}/invite ─────────────────────────────────────

async def test_invite_to_group_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 10a - POST - 201 Created - Admin invites user
    resp = await client.post(f"/api/groups/{gid}/invite", json={"email": "bob@test.com", "role": "member"}, headers=auth_headers)
    assert resp.status_code == 201

    # Test 10b - POST - 409 Conflict - Duplicate invite
    resp = await client.post(f"/api/groups/{gid}/invite", json={"email": "bob@test.com", "role": "member"}, headers=auth_headers)
    assert resp.status_code == 409

    # Test 10c - POST - 404 Not Found - Email not registered
    resp = await client.post(f"/api/groups/{gid}/invite", json={"email": "ghost@test.com", "role": "member"}, headers=auth_headers)
    assert resp.status_code == 404

    # Test 10d - POST - 422 Unprocessable Entity - Invalid role
    resp = await client.post(f"/api/groups/{gid}/invite", json={"email": "bob@test.com", "role": "superadmin"}, headers=auth_headers)
    assert resp.status_code in (409, 422)


# ── PATCH /api/groups/{group_id}/members/{member_id}/role ──────────────────

async def test_update_group_member_role_patch(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]
    await _invite_and_accept_group(client, auth_headers, second_auth_headers, gid, "bob@test.com", "member")
    members_resp = await client.get(f"/api/groups/{gid}/members", headers=auth_headers)
    bob = next(m for m in members_resp.json() if m["user"]["email"] == "bob@test.com")

    # Test 11a - PATCH - 200 OK - Admin changes role
    resp = await client.patch(f"/api/groups/{gid}/members/{bob['id']}/role", headers=auth_headers, json={"role": "admin"})
    assert resp.status_code == 200

    # Test 11b - PATCH - 422 Unprocessable Entity - Invalid role
    resp = await client.patch(f"/api/groups/{gid}/members/{bob['id']}/role", headers=auth_headers, json={"role": "superadmin"})
    assert resp.status_code == 422


# ── DELETE /api/groups/{group_id}/members/{member_id} ──────────────────────

async def test_remove_group_member_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]
    await _invite_and_accept_group(client, auth_headers, second_auth_headers, gid, "bob@test.com", "member")
    members_resp = await client.get(f"/api/groups/{gid}/members", headers=auth_headers)
    bob = next(m for m in members_resp.json() if m["user"]["email"] == "bob@test.com")
    alice = next(m for m in members_resp.json() if m["user"]["email"] == "alice@test.com")

    # Test 12a - DELETE - 400 Bad Request - Cannot remove self
    resp = await client.delete(f"/api/groups/{gid}/members/{alice['id']}", headers=auth_headers)
    assert resp.status_code == 400

    # Test 12b - DELETE - 204 No Content - Admin removes member
    resp = await client.delete(f"/api/groups/{gid}/members/{bob['id']}", headers=auth_headers)
    assert resp.status_code == 204


# ── GET /api/groups/{group_id}/trips ───────────────────────────────────────

async def test_list_group_trips_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 13a - GET - 200 OK - Empty trips list
    resp = await client.get(f"/api/groups/{gid}/trips", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 13b - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/groups/{gid}/trips", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/groups/{group_id}/trips/{trip_id} ───────────────────────────

async def test_attach_trip_to_group_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]
    trip = await create_trip(client, auth_headers, name="Attachable")
    tid = trip["id"]

    # Test 14a - POST - 200 OK - Admin attaches trip to group
    resp = await client.post(f"/api/groups/{gid}/trips/{tid}", headers=auth_headers)
    assert resp.status_code == 200

    # Test 14b - POST - 200 OK - Idempotent attach
    resp = await client.post(f"/api/groups/{gid}/trips/{tid}", headers=auth_headers)
    assert resp.status_code == 200

    # Test 14c - POST - 403 Forbidden - Non-admin group member
    await _invite_and_accept_group(client, auth_headers, second_auth_headers, gid, "bob@test.com", "member")
    trip2 = await create_trip(client, auth_headers, name="Another")
    resp = await client.post(f"/api/groups/{gid}/trips/{trip2['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


# ── DELETE /api/groups/{group_id}/trips/{trip_id} ──────────────────────────

async def test_detach_trip_from_group_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]
    trip = await create_trip(client, auth_headers, name="Detachable")
    tid = trip["id"]
    await client.post(f"/api/groups/{gid}/trips/{tid}", headers=auth_headers)

    # Test 15a - DELETE - 204 No Content - Admin detaches trip
    resp = await client.delete(f"/api/groups/{gid}/trips/{tid}", headers=auth_headers)
    assert resp.status_code == 204

    # Test 15b - DELETE - 404 Not Found - Trip not attached
    resp = await client.delete(f"/api/groups/{gid}/trips/{tid}", headers=auth_headers)
    assert resp.status_code == 404


# ── GET /api/groups/{group_id}/ideas ───────────────────────────────────────

async def test_get_group_idea_library_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 16a - GET - 200 OK - Empty library
    resp = await client.get(f"/api/groups/{gid}/ideas", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 16b - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/groups/{gid}/ideas", headers=second_auth_headers)
    assert resp.status_code == 403


# ── GET /api/groups/{group_id}/tags ────────────────────────────────────────

async def test_list_group_tags_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    group = await _create_group(client, auth_headers)
    gid = group["id"]

    # Test 17a - GET - 200 OK - Empty tags
    resp = await client.get(f"/api/groups/{gid}/tags", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 17b - GET - 403 Forbidden - Non-member
    resp = await client.get(f"/api/groups/{gid}/tags", headers=second_auth_headers)
    assert resp.status_code == 403
