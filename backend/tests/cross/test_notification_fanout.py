"""End-to-end notification fan-out across actions."""
from datetime import datetime, timedelta, date
import pytest

from app.schemas.notification import NotificationType


async def mk_trip(client, headers, name="T", **extra):
    body = {"name": name, **extra}
    r = await client.post("/api/trips/", json=body, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


async def invite(client, admin, trip_id, email, role="view_with_vote"):
    return await client.post(
        f"/api/trips/{trip_id}/invite",
        json={"email": email, "role": role},
        headers=admin,
    )


async def invite_accept(client, admin, invitee, trip_id, email, role="view_with_vote"):
    r = await invite(client, admin, trip_id, email, role)
    mid = r.json()["id"]
    await client.post(f"/api/trips/invitations/{mid}/accept", headers=invitee)
    return mid


async def inbox(client, headers):
    return (await client.get("/api/notifications/", headers=headers)).json()


def types_of(inbox_rows) -> list[str]:
    return [n["type"] for n in inbox_rows]


# ── Trip lifecycle ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trip_created_self_only(
    client, auth_headers, second_auth_headers
):
    await mk_trip(client, auth_headers, "Mine")
    alice = await inbox(client, auth_headers)
    bob = await inbox(client, second_auth_headers)
    assert any(n["type"] == "trip_created" for n in alice)
    assert all(n["type"] != "trip_created" for n in bob)


@pytest.mark.asyncio
async def test_trip_renamed_fanout(client, auth_headers, second_auth_headers):
    trip = await mk_trip(client, auth_headers, "Old")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.patch(f"/api/trips/{trip['id']}", json={"name": "New"}, headers=auth_headers)
    assert any(n["type"] == "trip_renamed" for n in await inbox(client, auth_headers))
    assert any(n["type"] == "trip_renamed" for n in await inbox(client, second_auth_headers))


@pytest.mark.asyncio
async def test_trip_date_changed_fanout(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(
        client, auth_headers, "Dated",
        start_date=datetime.combine(date.today(), datetime.min.time()).isoformat(),
    )
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.patch(
        f"/api/trips/{trip['id']}",
        json={"start_date": (datetime.combine(date.today() + timedelta(days=3), datetime.min.time())).isoformat()},
        headers=auth_headers,
    )
    assert any(n["type"] == "trip_date_changed" for n in await inbox(client, auth_headers))
    assert any(n["type"] == "trip_date_changed" for n in await inbox(client, second_auth_headers))


@pytest.mark.asyncio
async def test_trip_deleted_fanout(client, auth_headers, second_auth_headers):
    trip = await mk_trip(client, auth_headers, "Doomed")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert any(n["type"] == "trip_deleted" and n["payload"].get("self")
               for n in await inbox(client, auth_headers))
    assert any(n["type"] == "trip_deleted" for n in await inbox(client, second_auth_headers))


# ── Members ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_received_to_invitee_only(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    trip = await mk_trip(client, auth_headers, "Inv")
    await invite(client, auth_headers, trip["id"], "bob@test.com")
    assert any(n["type"] == "invite_received" for n in await inbox(client, second_auth_headers))
    assert all(n["type"] != "invite_received" for n in await inbox(client, third_auth_headers))


@pytest.mark.asyncio
async def test_invite_accepted_two_shapes(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "Inv")
    r = await invite(client, auth_headers, trip["id"], "bob@test.com")
    mid = r.json()["id"]
    await client.post(f"/api/trips/invitations/{mid}/accept", headers=second_auth_headers)
    bob = [n for n in await inbox(client, second_auth_headers) if n["type"] == "invite_accepted"]
    alice = [n for n in await inbox(client, auth_headers) if n["type"] == "invite_accepted"]
    assert any(n["payload"].get("self") for n in bob)
    assert any(n["payload"].get("joined_user_name") for n in alice)


@pytest.mark.asyncio
async def test_invite_declined_to_admins(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "Inv")
    r = await invite(client, auth_headers, trip["id"], "bob@test.com")
    mid = r.json()["id"]
    await client.delete(
        f"/api/trips/invitations/{mid}/decline", headers=second_auth_headers
    )
    assert any(n["type"] == "invite_declined" for n in await inbox(client, auth_headers))


@pytest.mark.asyncio
async def test_role_changed_notifies_target(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "T")
    mid = (await invite(client, auth_headers, trip["id"], "bob@test.com", role="view_only")).json()["id"]
    await client.post(f"/api/trips/invitations/{mid}/accept", headers=second_auth_headers)
    await client.patch(
        f"/api/trips/{trip['id']}/members/{mid}/role",
        json={"role": "view_with_vote"},
        headers=auth_headers,
    )
    bob = await inbox(client, second_auth_headers)
    assert any(n["type"] == "member_role_changed" for n in bob)


@pytest.mark.asyncio
async def test_member_removed_two_shapes(
    client, auth_headers, second_auth_headers, third_auth_headers
):
    trip = await mk_trip(client, auth_headers, "T")
    mid_bob = await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await invite_accept(client, auth_headers, third_auth_headers, trip["id"], "carol@test.com")
    await client.delete(
        f"/api/trips/{trip['id']}/members/{mid_bob}", headers=auth_headers
    )
    bob_n = [n for n in await inbox(client, second_auth_headers) if n["type"] == "member_removed"]
    carol_n = [n for n in await inbox(client, third_auth_headers) if n["type"] == "member_removed"]
    assert any(n["payload"].get("self") for n in bob_n)
    assert any(n["payload"].get("removed_user_name") for n in carol_n)


# ── Events ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_added_notifies_others_not_creator(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "T")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "Dinner"},
        headers=auth_headers,
    )
    alice = [n for n in await inbox(client, auth_headers) if n["type"] == "event_added"]
    bob = [n for n in await inbox(client, second_auth_headers) if n["type"] == "event_added"]
    assert alice == []
    assert bob


@pytest.mark.asyncio
async def test_event_title_only_edit_skips_moved(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "T")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    ev = (await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "A"},
        headers=auth_headers,
    )).json()
    await client.patch(f"/api/events/{ev['id']}", json={"title": "B"}, headers=auth_headers)
    bob = [n for n in await inbox(client, second_auth_headers) if n["type"] == "event_moved"]
    assert bob == []


@pytest.mark.asyncio
async def test_event_time_change_fires_moved(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "T")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    ev = (await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "A"},
        headers=auth_headers,
    )).json()
    await client.patch(
        f"/api/events/{ev['id']}",
        json={"start_time": "2026-05-01T10:00:00"},
        headers=auth_headers,
    )
    bob = [n for n in await inbox(client, second_auth_headers) if n["type"] == "event_moved"]
    assert bob


@pytest.mark.asyncio
async def test_event_delete_fires_removed(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "T")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    ev = (await client.post(
        "/api/events/", json={"trip_id": trip["id"], "title": "A"}, headers=auth_headers
    )).json()
    await client.delete(f"/api/events/{ev['id']}", headers=auth_headers)
    bob = [n for n in await inbox(client, second_auth_headers) if n["type"] == "event_removed"]
    assert bob and not bob[0]["payload"].get("moved_to_bin")


@pytest.mark.asyncio
async def test_event_move_to_bin_fires_removed_with_flag(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "T")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    ev = (await client.post(
        "/api/events/", json={"trip_id": trip["id"], "title": "A"}, headers=auth_headers
    )).json()
    await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    bob = [n for n in await inbox(client, second_auth_headers) if n["type"] == "event_removed"]
    assert any(n["payload"].get("moved_to_bin") for n in bob)


# ── Ripple ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ripple_notifies_members(
    client, auth_headers, second_auth_headers
):
    today_iso = date.today().isoformat()
    trip = await mk_trip(client, auth_headers, "T", start_date=today_iso)
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    # Create a future event
    start = (datetime.now() + timedelta(hours=2)).isoformat()
    await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "Later", "day_date": today_iso,
              "start_time": start},
        headers=auth_headers,
    )
    await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 15},
        headers=auth_headers,
    )
    bob = [n for n in await inbox(client, second_auth_headers) if n["type"] == "ripple_fired"]
    assert bob


# ── Groups ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_group_created_self_only(
    client, auth_headers, second_auth_headers
):
    await client.post("/api/groups/", json={"name": "G"}, headers=auth_headers)
    alice = await inbox(client, auth_headers)
    bob = await inbox(client, second_auth_headers)
    assert any(n["type"] == "group_created" for n in alice)
    assert all(n["type"] != "group_created" for n in bob)


@pytest.mark.asyncio
async def test_group_invite_received(
    client, auth_headers, second_auth_headers
):
    g = (await client.post("/api/groups/", json={"name": "G"}, headers=auth_headers)).json()
    await client.post(
        f"/api/groups/{g['id']}/invite",
        json={"email": "bob@test.com"},
        headers=auth_headers,
    )
    assert any(n["type"] == "group_invite_received" for n in await inbox(client, second_auth_headers))


# ── Brainstorm promotion ──────────────────────────────────────────────────────

_SAMPLE_ITEM = {
    "title": "Grand Palace",
    "description": "Royal complex",
    "category": "sight",
}


@pytest.mark.asyncio
async def test_brainstorm_promote_notifies_peers_not_promoter(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "BS")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    alice_notifs = [n for n in await inbox(client, auth_headers) if n["type"] == "brainstorm_promoted"]
    bob_notifs = [n for n in await inbox(client, second_auth_headers) if n["type"] == "brainstorm_promoted"]
    assert alice_notifs == []
    assert len(bob_notifs) == 1


@pytest.mark.asyncio
async def test_brainstorm_promote_notification_payload(
    client, auth_headers, second_auth_headers
):
    trip = await mk_trip(client, auth_headers, "Payload")
    await invite_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    bob_notifs = [n for n in await inbox(client, second_auth_headers) if n["type"] == "brainstorm_promoted"]
    payload = bob_notifs[0]["payload"]
    assert payload["trip_name"] == "Payload"
    assert payload["count"] == 1
    assert "Grand Palace" in payload["titles"]
    assert payload["actor_name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_brainstorm_promote_no_notification_when_solo(
    client, auth_headers
):
    trip = await mk_trip(client, auth_headers, "Solo")
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    alice_notifs = [n for n in await inbox(client, auth_headers) if n["type"] == "brainstorm_promoted"]
    assert alice_notifs == []


# ── Disabled type suppression ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_disabled_type_is_suppressed(
    client, auth_headers, monkeypatch
):
    monkeypatch.setitem(NotificationType.ENABLED, NotificationType.TRIP_CREATED, False)
    await mk_trip(client, auth_headers, "Silent")
    assert all(n["type"] != "trip_created" for n in await inbox(client, auth_headers))
