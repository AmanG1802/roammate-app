"""§11 Notification Fanout — end-to-end notification fan-out across trip/group actions."""
from __future__ import annotations

from datetime import datetime, timedelta, date

import pytest
from httpx import AsyncClient

from app.schemas.notification import NotificationType
from tests.conftest import create_trip


async def _invite(client, admin, trip_id, email, role="view_with_vote"):
    return await client.post(f"/api/trips/{trip_id}/invite", json={"email": email, "role": role}, headers=admin)


async def _invite_accept(client, admin, invitee, trip_id, email, role="view_with_vote"):
    r = await _invite(client, admin, trip_id, email, role)
    mid = r.json()["id"]
    await client.post(f"/api/trips/invitations/{mid}/accept", headers=invitee)
    return mid


async def _inbox(client, headers):
    return (await client.get("/api/notifications", headers=headers)).json()


async def test_trip_created_self_only(client: AsyncClient, auth_headers, second_auth_headers):
    await create_trip(client, auth_headers, name="Mine")
    alice = await _inbox(client, auth_headers)
    bob = await _inbox(client, second_auth_headers)
    assert any(n["type"] == "trip_created" for n in alice)
    assert all(n["type"] != "trip_created" for n in bob)


async def test_trip_renamed_fanout(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers, name="Old")
    await _invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.patch(f"/api/trips/{trip['id']}", json={"name": "New"}, headers=auth_headers)
    assert any(n["type"] == "trip_renamed" for n in await _inbox(client, second_auth_headers))


async def test_trip_deleted_fanout(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers, name="Doomed")
    await _invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert any(n["type"] == "trip_deleted" for n in await _inbox(client, second_auth_headers))


async def test_invite_declined_to_admins(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    r = await _invite(client, auth_headers, trip["id"], "bob@test.com")
    mid = r.json()["id"]
    await client.delete(f"/api/trips/invitations/{mid}/decline", headers=second_auth_headers)
    assert any(n["type"] == "invite_declined" for n in await _inbox(client, auth_headers))


async def test_role_changed_notifies_target(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    mid = (await _invite(client, auth_headers, trip["id"], "bob@test.com", "view_only")).json()["id"]
    await client.post(f"/api/trips/invitations/{mid}/accept", headers=second_auth_headers)
    await client.patch(f"/api/trips/{trip['id']}/members/{mid}/role", json={"role": "view_with_vote"}, headers=auth_headers)
    assert any(n["type"] == "member_role_changed" for n in await _inbox(client, second_auth_headers))


async def test_member_removed_two_shapes(client: AsyncClient, auth_headers, second_auth_headers, third_auth_headers):
    trip = await create_trip(client, auth_headers)
    mid_bob = await _invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await _invite_accept(client, auth_headers, third_auth_headers, trip["id"], "carol@test.com")
    await client.delete(f"/api/trips/{trip['id']}/members/{mid_bob}", headers=auth_headers)
    bob_n = [n for n in await _inbox(client, second_auth_headers) if n["type"] == "member_removed"]
    carol_n = [n for n in await _inbox(client, third_auth_headers) if n["type"] == "member_removed"]
    assert any(n["payload"].get("self") for n in bob_n)
    assert any(n["payload"].get("removed_user_name") for n in carol_n)


async def test_event_added_notifies_others_not_creator(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await _invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.post("/api/events", json={"trip_id": trip["id"], "title": "Dinner"}, headers=auth_headers)
    alice = [n for n in await _inbox(client, auth_headers) if n["type"] == "event_added"]
    bob = [n for n in await _inbox(client, second_auth_headers) if n["type"] == "event_added"]
    assert alice == []
    assert bob


async def test_brainstorm_promote_notifies_peers_not_promoter(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await _invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [{"title": "Spot", "category": "sight"}]}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)
    alice = [n for n in await _inbox(client, auth_headers) if n["type"] == "brainstorm_promoted"]
    bob = [n for n in await _inbox(client, second_auth_headers) if n["type"] == "brainstorm_promoted"]
    assert alice == []
    assert len(bob) == 1


async def test_group_created_self_only(client: AsyncClient, auth_headers, second_auth_headers):
    await client.post("/api/groups", json={"name": "G"}, headers=auth_headers)
    alice = await _inbox(client, auth_headers)
    bob = await _inbox(client, second_auth_headers)
    assert any(n["type"] == "group_created" for n in alice)
    assert all(n["type"] != "group_created" for n in bob)


async def test_disabled_type_is_suppressed(client: AsyncClient, auth_headers, monkeypatch):
    monkeypatch.setitem(NotificationType.ENABLED, NotificationType.TRIP_CREATED, False)
    await create_trip(client, auth_headers, name="Silent")
    assert all(n["type"] != "trip_created" for n in await _inbox(client, auth_headers))
