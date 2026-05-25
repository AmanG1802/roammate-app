"""API tests for trips.py — trip CRUD, members, invitations, idea bin, days."""

import pytest
from httpx import AsyncClient
from tests.conftest import create_trip, invite_and_accept

NO_AUTH = {"Cookie": "", "Authorization": ""}


# ── GET /api/trips ─────────────────────────────────────────────────────────

async def test_get_my_trips_get(client: AsyncClient, auth_headers: dict):
    # Test 1a - GET - 200 OK - No trips returns empty list
    resp = await client.get("/api/trips", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 1b - GET - 200 OK - Returns trips after creation
    await create_trip(client, auth_headers, name="Trip A")
    resp = await client.get("/api/trips", headers=auth_headers)
    assert resp.status_code == 200
    trips = resp.json()
    assert len(trips) >= 1
    assert any(t["name"] == "Trip A" for t in trips)

    # Test 1c - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/trips", headers=NO_AUTH)
    assert resp.status_code == 401


# ── POST /api/trips ────────────────────────────────────────────────────────

async def test_create_trip_post(client: AsyncClient, auth_headers: dict):
    # Test 2a - POST - 201 Created - Create trip with valid payload
    resp = await client.post("/api/trips", json={"name": "Paris Trip"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Paris Trip"
    assert "id" in data

    # Test 2b - POST - 201 Created - Create trip with start_date auto-creates Day 1
    resp = await client.post("/api/trips", json={
        "name": "Dated Trip", "start_date": "2025-06-01T00:00:00",
    }, headers=auth_headers)
    assert resp.status_code == 201
    trip_id = resp.json()["id"]
    days_resp = await client.get(f"/api/trips/{trip_id}/days", headers=auth_headers)
    assert days_resp.status_code == 200
    assert len(days_resp.json()) >= 1

    # Test 2c - POST - 422 Unprocessable Entity - Missing name field
    resp = await client.post("/api/trips", json={}, headers=auth_headers)
    assert resp.status_code == 422

    # Test 2d - POST - 401 Unauthorized - No auth
    resp = await client.post("/api/trips", json={"name": "Hack"}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/trips/{trip_id} ───────────────────────────────────────────────

async def test_get_trip_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 3a - GET - 200 OK - Owner can get trip details
    resp = await client.get(f"/api/trips/{trip_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == trip_id

    # Test 3b - GET - 403 Forbidden - Non-member cannot access trip
    resp = await client.get(f"/api/trips/{trip_id}", headers=second_auth_headers)
    assert resp.status_code == 403

    # Test 3c - GET - 401 Unauthorized - No auth
    resp = await client.get(f"/api/trips/{trip_id}", headers=NO_AUTH)
    assert resp.status_code == 401


# ── PATCH /api/trips/{trip_id} ─────────────────────────────────────────────

async def test_update_trip_patch(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 4a - PATCH - 200 OK - Admin can rename trip
    resp = await client.patch(f"/api/trips/{trip_id}", headers=auth_headers, json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"

    # Test 4b - PATCH - 403 Forbidden - Non-admin cannot update trip
    await invite_and_accept(client, auth_headers, second_auth_headers, trip_id, "bob@test.com", "view_only")
    resp = await client.patch(f"/api/trips/{trip_id}", headers=second_auth_headers, json={"name": "Hacked"})
    assert resp.status_code == 403

    # Test 4c - PATCH - 401 Unauthorized - No auth
    resp = await client.patch(f"/api/trips/{trip_id}", json={"name": "x"}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── DELETE /api/trips/{trip_id} ────────────────────────────────────────────

async def test_delete_trip_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 5a - DELETE - 403 Forbidden - Non-admin cannot delete
    await invite_and_accept(client, auth_headers, second_auth_headers, trip_id, "bob@test.com", "view_only")
    resp = await client.delete(f"/api/trips/{trip_id}", headers=second_auth_headers)
    assert resp.status_code == 403

    # Test 5b - DELETE - 204 No Content - Admin deletes trip
    resp = await client.delete(f"/api/trips/{trip_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Test 5c - DELETE - 401 Unauthorized - No auth
    resp = await client.delete(f"/api/trips/{trip_id}", headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/trips/invitations/pending ─────────────────────────────────────

async def test_get_my_invitations_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 6a - GET - 200 OK - No pending invitations
    resp = await client.get("/api/trips/invitations/pending", headers=second_auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 6b - GET - 200 OK - Returns pending invitation after invite
    await client.post(f"/api/trips/{trip_id}/invite", json={"email": "bob@test.com", "role": "view_only"}, headers=auth_headers)
    resp = await client.get("/api/trips/invitations/pending", headers=second_auth_headers)
    assert resp.status_code == 200
    invites = resp.json()
    assert len(invites) == 1
    assert invites[0]["trip_id"] == trip_id


# ── POST /api/trips/invitations/{member_id}/accept ────────────────────────

async def test_accept_invitation_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]
    inv_resp = await client.post(f"/api/trips/{trip_id}/invite", json={"email": "bob@test.com", "role": "view_only"}, headers=auth_headers)
    member_id = inv_resp.json()["id"]

    # Test 7a - POST - 200 OK - Accept pending invitation
    resp = await client.post(f"/api/trips/invitations/{member_id}/accept", headers=second_auth_headers)
    assert resp.status_code == 200

    # Test 7b - POST - 404 Not Found - Accept already accepted invitation
    resp = await client.post(f"/api/trips/invitations/{member_id}/accept", headers=second_auth_headers)
    assert resp.status_code == 404

    # Test 7c - POST - 404 Not Found - Invalid member_id
    resp = await client.post("/api/trips/invitations/999999/accept", headers=second_auth_headers)
    assert resp.status_code == 404


# ── DELETE /api/trips/invitations/{member_id}/decline ──────────────────────

async def test_decline_invitation_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]
    inv_resp = await client.post(f"/api/trips/{trip_id}/invite", json={"email": "bob@test.com", "role": "view_only"}, headers=auth_headers)
    member_id = inv_resp.json()["id"]

    # Test 8a - DELETE - 204 No Content - Decline invitation
    resp = await client.delete(f"/api/trips/invitations/{member_id}/decline", headers=second_auth_headers)
    assert resp.status_code == 204

    # Test 8b - DELETE - 404 Not Found - Decline already declined
    resp = await client.delete(f"/api/trips/invitations/{member_id}/decline", headers=second_auth_headers)
    assert resp.status_code == 404


# ── GET /api/trips/{trip_id}/members ───────────────────────────────────────

async def test_get_trip_members_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 9a - GET - 200 OK - Owner sees themselves
    resp = await client.get(f"/api/trips/{trip_id}/members", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Test 9b - GET - 403 Forbidden - Non-member cannot list members
    resp = await client.get(f"/api/trips/{trip_id}/members", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/trips/{trip_id}/invite ───────────────────────────────────────

async def test_invite_to_trip_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 10a - POST - 201 Created - Admin invites user
    resp = await client.post(f"/api/trips/{trip_id}/invite", json={"email": "bob@test.com", "role": "view_only"}, headers=auth_headers)
    assert resp.status_code == 201

    # Test 10b - POST - 409 Conflict - Duplicate invite
    resp = await client.post(f"/api/trips/{trip_id}/invite", json={"email": "bob@test.com", "role": "view_only"}, headers=auth_headers)
    assert resp.status_code == 409

    # Test 10c - POST - 404 Not Found - Invitee email does not exist
    resp = await client.post(f"/api/trips/{trip_id}/invite", json={"email": "ghost@test.com", "role": "view_only"}, headers=auth_headers)
    assert resp.status_code == 404

    # Test 10d - POST - 422 Unprocessable Entity - Invalid role
    resp = await client.post(f"/api/trips/{trip_id}/invite", json={"email": "bob@test.com", "role": "superadmin"}, headers=auth_headers)
    assert resp.status_code in (409, 422)

    # Test 10e - POST - 403 Forbidden - Non-admin tries to invite (on a fresh trip)
    trip2 = await create_trip(client, auth_headers, name="Another Trip")
    await invite_and_accept(client, auth_headers, second_auth_headers, trip2["id"], "bob@test.com", "view_only")
    resp = await client.post(f"/api/trips/{trip2['id']}/invite", json={"email": "alice@test.com", "role": "view_only"}, headers=second_auth_headers)
    assert resp.status_code == 403


# ── PATCH /api/trips/{trip_id}/members/{member_id}/role ────────────────────

async def test_update_member_role_patch(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]
    await invite_and_accept(client, auth_headers, second_auth_headers, trip_id, "bob@test.com", "view_only")
    members_resp = await client.get(f"/api/trips/{trip_id}/members", headers=auth_headers)
    bob_member = next(m for m in members_resp.json() if m["user"]["email"] == "bob@test.com")

    # Test 11a - PATCH - 200 OK - Admin changes member role
    resp = await client.patch(f"/api/trips/{trip_id}/members/{bob_member['id']}/role", headers=auth_headers, json={"role": "view_with_vote"})
    assert resp.status_code == 200

    # Test 11b - PATCH - 403 Forbidden - Non-admin tries to change role
    resp = await client.patch(f"/api/trips/{trip_id}/members/{bob_member['id']}/role", headers=second_auth_headers, json={"role": "admin"})
    assert resp.status_code == 403

    # Test 11c - PATCH - 422 Unprocessable Entity - Invalid role value
    resp = await client.patch(f"/api/trips/{trip_id}/members/{bob_member['id']}/role", headers=auth_headers, json={"role": "superadmin"})
    assert resp.status_code == 422


# ── DELETE /api/trips/{trip_id}/members/{member_id} ────────────────────────

async def test_remove_trip_member_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]
    await invite_and_accept(client, auth_headers, second_auth_headers, trip_id, "bob@test.com", "view_only")
    members_resp = await client.get(f"/api/trips/{trip_id}/members", headers=auth_headers)
    bob_member = next(m for m in members_resp.json() if m["user"]["email"] == "bob@test.com")
    alice_member = next(m for m in members_resp.json() if m["user"]["email"] == "alice@test.com")

    # Test 12a - DELETE - 400 Bad Request - Admin cannot remove self
    resp = await client.delete(f"/api/trips/{trip_id}/members/{alice_member['id']}", headers=auth_headers)
    assert resp.status_code == 400

    # Test 12b - DELETE - 204 No Content - Admin removes other member
    resp = await client.delete(f"/api/trips/{trip_id}/members/{bob_member['id']}", headers=auth_headers)
    assert resp.status_code == 204


# ── GET /api/trips/{trip_id}/ideas ─────────────────────────────────────────

async def test_get_idea_bin_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 13a - GET - 200 OK - Empty idea bin
    resp = await client.get(f"/api/trips/{trip_id}/ideas", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Test 13b - GET - 403 Forbidden - Non-member access
    resp = await client.get(f"/api/trips/{trip_id}/ideas", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/trips/{trip_id}/ingest ───────────────────────────────────────

async def test_ingest_to_idea_bin_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers)
    trip_id = trip["id"]

    # Test 14a - POST - 200 OK - Ingest text to idea bin
    resp = await client.post(f"/api/trips/{trip_id}/ingest", headers=auth_headers, json={
        "text": "Visit the Eiffel Tower",
    })
    assert resp.status_code == 200

    # Test 14b - POST - 403 Forbidden - Non-member cannot ingest
    resp = await client.post(f"/api/trips/{trip_id}/ingest", headers=second_auth_headers, json={
        "text": "Hacked idea",
    })
    assert resp.status_code == 403


# ── GET /api/trips/{trip_id}/days ──────────────────────────────────────────

async def test_get_trip_days_get(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Day Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]

    # Test 15a - GET - 200 OK - Returns at least Day 1
    resp = await client.get(f"/api/trips/{trip_id}/days", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # Test 15b - GET - 403 Forbidden - Non-member access
    resp = await client.get(f"/api/trips/{trip_id}/days", headers=second_auth_headers)
    assert resp.status_code == 403


# ── POST /api/trips/{trip_id}/days ─────────────────────────────────────────

async def test_add_trip_day_post(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Day Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]

    # Test 16a - POST - 201 Created - Admin adds a new day
    resp = await client.post(f"/api/trips/{trip_id}/days", headers=auth_headers, json={"date": "2025-06-02"})
    assert resp.status_code == 201

    # Test 16b - POST - 409 Conflict - Duplicate date
    resp = await client.post(f"/api/trips/{trip_id}/days", headers=auth_headers, json={"date": "2025-06-02"})
    assert resp.status_code == 409

    # Test 16c - POST - 403 Forbidden - Non-admin cannot add day
    await invite_and_accept(client, auth_headers, second_auth_headers, trip_id, "bob@test.com", "view_only")
    resp = await client.post(f"/api/trips/{trip_id}/days", headers=second_auth_headers, json={"date": "2025-06-03"})
    assert resp.status_code == 403


# ── DELETE /api/trips/{trip_id}/days/{day_id} ──────────────────────────────

async def test_delete_trip_day_delete(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    trip = await create_trip(client, auth_headers, name="Day Trip", start_date="2025-06-01T00:00:00")
    trip_id = trip["id"]
    add_resp = await client.post(f"/api/trips/{trip_id}/days", headers=auth_headers, json={"date": "2025-06-02"})
    day_id = add_resp.json()["id"]

    # Test 17a - DELETE - 204 No Content - Admin deletes day
    resp = await client.delete(f"/api/trips/{trip_id}/days/{day_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Test 17b - DELETE - 404 Not Found - Already deleted
    resp = await client.delete(f"/api/trips/{trip_id}/days/{day_id}", headers=auth_headers)
    assert resp.status_code == 404

    # Test 17c - DELETE - 403 Forbidden - Non-admin cannot delete day
    add_resp2 = await client.post(f"/api/trips/{trip_id}/days", headers=auth_headers, json={"date": "2025-06-03"})
    day_id2 = add_resp2.json()["id"]
    await invite_and_accept(client, auth_headers, second_auth_headers, trip_id, "bob@test.com", "view_only")
    resp = await client.delete(f"/api/trips/{trip_id}/days/{day_id2}", headers=second_auth_headers)
    assert resp.status_code == 403
