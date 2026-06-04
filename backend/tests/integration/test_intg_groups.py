"""§12 Groups — CRUD, invitations, roles, trip attachment, IDOR, and group library."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip


async def _mk_group(client, headers, name="G"):
    r = await client.post("/api/groups", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()


async def _invite_group_accept(client, admin, invitee, group_id, email, role="member"):
    r = await client.post(f"/api/groups/{group_id}/invite", json={"email": email, "role": role}, headers=admin)
    assert r.status_code == 201
    pending = (await client.get("/api/groups/invitations/pending", headers=invitee)).json()
    mid = [p["id"] for p in pending if p["group_id"] == group_id][0]
    await client.post(f"/api/groups/invitations/{mid}/accept", headers=invitee)
    return mid


async def test_create_group(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers, "Travel Crew")
    assert g["name"] == "Travel Crew"


async def test_list_groups(client: AsyncClient, auth_headers, second_auth_headers):
    await _mk_group(client, auth_headers, "A")
    await _mk_group(client, second_auth_headers, "B")
    alice = (await client.get("/api/groups", headers=auth_headers)).json()
    names = [g["name"] for g in alice]
    assert "A" in names and "B" not in names


async def test_get_group_detail(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    resp = await client.get(f"/api/groups/{g['id']}", headers=auth_headers)
    assert resp.status_code == 200


async def test_update_group(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    resp = await client.patch(f"/api/groups/{g['id']}", json={"name": "Renamed"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


async def test_delete_group_admin_only(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers)
    await _invite_group_accept(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    assert (await client.delete(f"/api/groups/{g['id']}", headers=second_auth_headers)).status_code == 403
    assert (await client.delete(f"/api/groups/{g['id']}", headers=auth_headers)).status_code == 204


async def test_invite_to_group(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers)
    resp = await client.post(f"/api/groups/{g['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    assert resp.status_code == 201


async def test_accept_group_invite(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers)
    mid = await _invite_group_accept(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    members = (await client.get(f"/api/groups/{g['id']}/members", headers=auth_headers)).json()
    assert len(members) >= 2


async def test_decline_group_invite(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    pending = (await client.get("/api/groups/invitations/pending", headers=second_auth_headers)).json()
    mid = pending[0]["id"]
    resp = await client.delete(f"/api/groups/invitations/{mid}/decline", headers=second_auth_headers)
    assert resp.status_code in (200, 204)


async def test_list_pending_group_invitations(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    resp = await client.get("/api/groups/invitations/pending", headers=second_auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_attach_trip_to_group(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code in (200, 201, 204)


async def test_detach_trip_from_group(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    resp = await client.delete(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_list_group_trips(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    trips = (await client.get(f"/api/groups/{g['id']}/trips", headers=auth_headers)).json()
    assert any(t["id"] == trip["id"] for t in trips)


async def test_group_idor_blocked(client: AsyncClient, auth_headers, second_auth_headers):
    a = await _mk_group(client, auth_headers, "A")
    b = await _mk_group(client, second_auth_headers, "B")
    for path in ["", "/members", "/ideas", "/tags", "/trips"]:
        r = await client.get(f"/api/groups/{b['id']}{path}", headers=auth_headers)
        assert r.status_code == 403


# ── Group library ─────────────────────────────────────────────────────────────

async def test_group_idea_library_aggregates_across_trips(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "Pantheon"}, headers=auth_headers)
    lib = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    assert any(i["title"] == "Pantheon" for i in lib)


async def test_detach_trip_removes_ideas_from_library(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "Pantheon"}, headers=auth_headers)
    assert (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    await client.delete(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json() == []


# ── Group lifecycle ───────────────────────────────────────────────────────────

async def test_full_group_lifecycle(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers, "Rome Crew")
    await _invite_group_accept(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    trip = await create_trip(client, auth_headers, name="Rome 2026")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    group_trips = (await client.get(f"/api/groups/{g['id']}/trips", headers=second_auth_headers)).json()
    assert any(t["id"] == trip["id"] for t in group_trips)
    await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "Pantheon"}, headers=auth_headers)
    lib = (await client.get(f"/api/groups/{g['id']}/ideas", headers=second_auth_headers)).json()
    assert any(i["title"] == "Pantheon" for i in lib)
    await client.delete(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    assert (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json() == []
    assert (await client.delete(f"/api/groups/{g['id']}", headers=auth_headers)).status_code == 204
    assert (await client.get(f"/api/trips/{trip['id']}", headers=auth_headers)).status_code == 200


async def test_trip_delete_while_attached(client: AsyncClient, auth_headers):
    g = await _mk_group(client, auth_headers)
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    trips = (await client.get(f"/api/groups/{g['id']}/trips", headers=auth_headers)).json()
    assert all(t["id"] != trip["id"] for t in trips)


async def test_non_admin_cannot_detach_trip(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers)
    await _invite_group_accept(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    resp = await client.delete(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403
    trips = (await client.get(f"/api/groups/{g['id']}/trips", headers=auth_headers)).json()
    assert any(t["id"] == trip["id"] for t in trips)


async def test_removed_member_loses_read_access(client: AsyncClient, auth_headers, second_auth_headers):
    g = await _mk_group(client, auth_headers)
    mid = await _invite_group_accept(client, auth_headers, second_auth_headers, g["id"], "bob@test.com")
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "X"}, headers=auth_headers)
    await client.delete(f"/api/groups/{g['id']}/members/{mid}", headers=auth_headers)
    assert (await client.get(f"/api/groups/{g['id']}/ideas", headers=second_auth_headers)).status_code == 403
