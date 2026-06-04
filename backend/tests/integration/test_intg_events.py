"""§6 Events (Timeline Items) — CRUD, source idea promotion, vote transfer,
notifications, and move-to-bin.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def _ingest(client, headers, trip_id, title="X"):
    r = await client.post(f"/api/trips/{trip_id}/ingest", json={"text": title}, headers=headers)
    return r.json()[0]


async def _create_event(client, headers, trip_id, title="Dinner", source_idea_id=None, **kw):
    body = {"trip_id": trip_id, "title": title, **kw}
    if source_idea_id is not None:
        body["source_idea_id"] = source_idea_id
    r = await client.post("/api/events", json=body, headers=headers)
    assert r.status_code == 201
    return r.json()


async def test_create_event_basic(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    assert ev["title"] == "Dinner"
    assert ev["trip_id"] == trip["id"]


async def test_create_event_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post("/api/events", json={"trip_id": trip["id"], "title": "X"}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_create_event_from_source_idea(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"], "Colosseum")
    ev = await _create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    assert ev["title"] is not None


async def test_create_event_from_idea_transfers_votes(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await client.post(f"/api/ideas/{idea['id']}/vote", json={"value": 1}, headers=auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    tally = (await client.get(f"/api/events/{ev['id']}/votes", headers=auth_headers)).json()
    assert tally["up"] == 1


async def test_create_event_from_idea_removes_source(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    idea = await _ingest(client, auth_headers, trip["id"])
    await _create_event(client, auth_headers, trip["id"], source_idea_id=idea["id"])
    ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert all(i["id"] != idea["id"] for i in ideas)


async def test_update_event_fields(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    resp = await client.patch(f"/api/events/{ev['id']}", json={"title": "Brunch"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Brunch"


async def test_update_event_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    resp = await client.patch(f"/api/events/{ev['id']}", json={"title": "X"}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_update_event_nonexistent_404(client: AsyncClient, auth_headers):
    resp = await client.patch("/api/events/999999", json={"title": "X"}, headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_event(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    resp = await client.delete(f"/api/events/{ev['id']}", headers=auth_headers)
    assert resp.status_code in (200, 204)


async def test_delete_event_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    resp = await client.delete(f"/api/events/{ev['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_delete_event_nonexistent_404(client: AsyncClient, auth_headers):
    resp = await client.delete("/api/events/999999", headers=auth_headers)
    assert resp.status_code == 404


async def test_move_event_to_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    ev = await _create_event(client, auth_headers, trip["id"])
    resp = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    assert resp.status_code == 200
    idea = resp.json()
    assert idea["title"] == ev["title"]


async def test_move_event_to_bin_preserves_enrichment_fields(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [{
        "title": "Trevi", "place_id": "c1", "lat": 41.9, "lng": 12.48,
        "address": "Rome", "photo_url": "http://x.jpg", "rating": 4.7,
    }]}, headers=auth_headers)
    ideas = (await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)).json()
    ev = await _create_event(client, auth_headers, trip["id"], source_idea_id=ideas[0]["id"], title="Trevi")
    resp = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    restored = resp.json()
    assert restored["place_id"] == "c1"
    assert restored["lat"] == 41.9


async def test_get_events_for_trip(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _create_event(client, auth_headers, trip["id"])
    resp = await client.get(f"/api/events?trip_id={trip['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_get_events_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/events?trip_id={trip['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_get_events_empty_trip(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/events?trip_id={trip['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
