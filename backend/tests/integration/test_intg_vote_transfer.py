"""§10 Vote Transfer — idea↔event, move-to-bin, day-delete, and round-trip vote preservation."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def _ingest(client, headers, trip_id, title="X"):
    r = await client.post(f"/api/trips/{trip_id}/ingest", json={"text": title}, headers=headers)
    return r.json()[0]


async def _create_event(client, headers, trip_id, title="Dinner", source_idea_id=None):
    body = {"trip_id": trip_id, "title": title}
    if source_idea_id is not None:
        body["source_idea_id"] = source_idea_id
    r = await client.post("/api/events", json=body, headers=headers)
    assert r.status_code == 201
    return r.json()


# ── idea → event ──────────────────────────────────────────────────────────────

async def test_idea_to_event_vote_transfer(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    tally = (await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1


async def test_idea_to_event_preserves_per_user_values(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    tally = (await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1 and tally["down"] == 1


async def test_event_created_without_source(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    t = (await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)).json()
    assert t == {"up": 0, "down": 0, "my_vote": 0}


# ── event → bin ───────────────────────────────────────────────────────────────

async def test_event_to_bin_vote_transfer(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    idea_id = r.json()["id"]
    t = (await client.get(f"/api/ideas/{idea_id}/votes", headers=auth_headers)).json()
    assert t["up"] == 1


async def test_move_to_bin_preserves_up_and_down(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    ev = await _create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    t = (await client.get(f"/api/ideas/{r.json()['id']}/votes", headers=auth_headers)).json()
    assert t["up"] == 1 and t["down"] == 1


async def test_move_to_bin_no_votes_clean(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    t = (await client.get(f"/api/ideas/{r.json()['id']}/votes", headers=auth_headers)).json()
    assert t == {"up": 0, "down": 0, "my_vote": 0}


# ── round-trip ────────────────────────────────────────────────────────────────

async def test_round_trip_idea_event_bin_event(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"], title="RoundTrip")
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    assert r.status_code == 200
    idea = r.json()
    t = (await client.get(f"/api/ideas/{idea['id']}/votes", headers=auth_headers)).json()
    assert t["up"] == 1


async def test_move_to_bin_shows_in_group_library_with_tally(client: AsyncClient, auth_headers):
    g = (await client.post("/api/groups", json={"name": "G"}, headers=auth_headers)).json()
    trip = await create_trip(client, auth_headers, name="Rome")
    await client.post(f"/api/groups/{g['id']}/trips/{trip['id']}", headers=auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"], title="Spot")
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    body = (await client.get(f"/api/groups/{g['id']}/ideas", headers=auth_headers)).json()
    assert body[0]["title"] == "Spot"
    assert body[0]["up"] == 1


# ── create-event / move-to-bin response includes inline votes ─────────────────

async def test_create_event_response_includes_transferred_votes(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    assert ev["up"] == 1 and ev["down"] == 0 and ev["my_vote"] == 1


async def test_create_event_response_zero_votes_without_source(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    assert ev["up"] == 0 and ev["down"] == 0 and ev["my_vote"] == 0


async def test_move_to_bin_response_includes_votes(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    assert r.json()["up"] == 1 and r.json()["my_vote"] == 1


async def test_move_to_bin_my_vote_reflects_caller(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    ev = await _create_event(client, auth_headers, trip["id"])
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    r = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    assert r.json()["my_vote"] == 1


# ── day-delete vote transfer ──────────────────────────────────────────────────

async def test_day_delete_vote_transfer(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    ev = await _create_event(client, auth_headers, trip["id"], title="Beach")
    await client.patch(f"/api/events/{ev['id']}", json={"day_date": days[0]["date"]}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin", headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    t = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert t["up"] == 1


async def test_day_delete_bin_preserves_multi_user_votes(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", "view_with_vote")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    ev = await _create_event(client, auth_headers, trip["id"], title="Market")
    await client.patch(f"/api/events/{ev['id']}", json={"day_date": days[0]["date"]}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": 1}, headers=auth_headers)
    await client.post(f"/api/events/{ev['id']}/vote", json={"value": -1}, headers=second_auth_headers)
    await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin", headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    t = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert t["up"] == 1 and t["down"] == 1


async def test_day_delete_bin_zero_votes_clean(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    days = (await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)).json()
    ev = await _create_event(client, auth_headers, trip["id"], title="Park")
    await client.patch(f"/api/events/{ev['id']}", json={"day_date": days[0]["date"]}, headers=auth_headers)
    await client.delete(f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin", headers=auth_headers)
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    t = (await client.get(f"/api/ideas/{ideas[0]['id']}/votes", headers=auth_headers)).json()
    assert t == {"up": 0, "down": 0, "my_vote": 0}
