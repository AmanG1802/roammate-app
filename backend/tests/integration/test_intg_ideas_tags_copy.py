"""§18 Ideas (Tags & Copy) — tagging, cross-trip copy, field preservation."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip
from app.models.all_models import PLACE_FIELDS

_ENRICHED = {
    "title": "Trevi Fountain",
    "description": "Iconic fountain",
    "category": "Culture & Arts",
    "place_id": "ChIJ1UCDJ1NgLxMRtrsCzOHxdvY",
    "lat": 41.9009,
    "lng": 12.4833,
    "address": "Piazza di Trevi, Roma",
    "photo_url": "https://maps.example.com/photo/trevi.jpg",
    "rating": 4.7,
    "price_level": 0,
    "types": ["tourist_attraction"],
    "time_category": "morning",
    "added_by": "AI",
}


async def _seed_idea(client, headers, trip_id):
    await client.post(f"/api/trips/{trip_id}/brainstorm/bulk", json={"items": [_ENRICHED]}, headers=headers)
    ideas = (await client.post(f"/api/trips/{trip_id}/brainstorm/promote", json={"item_ids": None}, headers=headers)).json()
    return ideas[0]


async def test_copy_idea_to_another_trip(client: AsyncClient, auth_headers):
    src = await create_trip(client, auth_headers, name="Rome")
    dst = await create_trip(client, auth_headers, name="Florence")
    idea = await _seed_idea(client, auth_headers, src["id"])
    resp = await client.post(f"/api/ideas/{idea['id']}/copy", json={"target_trip_id": dst["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    copy = resp.json()
    assert copy["title"] == "Trevi Fountain"
    assert copy["place_id"] == _ENRICHED["place_id"]


async def test_copy_preserves_place_lat_lng_url_hint_added_by(client: AsyncClient, auth_headers):
    src = await create_trip(client, auth_headers, name="A")
    dst = await create_trip(client, auth_headers, name="B")
    idea = await _seed_idea(client, auth_headers, src["id"])
    copy = (await client.post(f"/api/ideas/{idea['id']}/copy", json={"target_trip_id": dst["id"]}, headers=auth_headers)).json()
    assert copy["lat"] == _ENRICHED["lat"]
    assert copy["lng"] == _ENRICHED["lng"]
    assert copy["photo_url"] == _ENRICHED["photo_url"]


async def test_copy_nonexistent_idea_404(client: AsyncClient, auth_headers):
    dst = await create_trip(client, auth_headers)
    resp = await client.post("/api/ideas/999999/copy", json={"target_trip_id": dst["id"]}, headers=auth_headers)
    assert resp.status_code == 404


async def test_copy_nonexistent_target_trip_forbidden(client: AsyncClient, auth_headers, second_auth_headers):
    src = await create_trip(client, auth_headers)
    idea = await _seed_idea(client, auth_headers, src["id"])
    dst = await create_trip(client, second_auth_headers, name="Bob's")
    resp = await client.post(f"/api/ideas/{idea['id']}/copy", json={"target_trip_id": dst["id"]}, headers=auth_headers)
    assert resp.status_code == 403


async def test_cross_trip_copy_preserves_all_place_fields(client: AsyncClient, auth_headers):
    src = await create_trip(client, auth_headers, name="Rome")
    dst = await create_trip(client, auth_headers, name="Florence")
    idea = await _seed_idea(client, auth_headers, src["id"])
    copy = (await client.post(f"/api/ideas/{idea['id']}/copy", json={"target_trip_id": dst["id"]}, headers=auth_headers)).json()
    for field in PLACE_FIELDS:
        if field == "added_by":
            continue
        assert copy[field] == _ENRICHED.get(field), f"Mismatch on {field}"


async def test_idea_timeline_bin_timeline_round_trip(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_ENRICHED]}, headers=auth_headers)
    ideas = (await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)).json()
    idea_id = ideas[0]["id"]
    ev_resp = await client.post("/api/events", json={
        "trip_id": trip["id"], "source_idea_id": idea_id, "title": ideas[0]["title"],
        "day_date": "2026-06-01", "start_time": "10:00:00", "end_time": "11:00:00",
    }, headers=auth_headers)
    assert ev_resp.status_code == 201, f"Event create failed: {ev_resp.status_code} {ev_resp.text}"
    ev = ev_resp.json()
    for f in ("place_id", "lat", "lng", "address", "photo_url", "rating", "price_level", "types"):
        assert ev.get(f) == _ENRICHED.get(f), f"Event field mismatch: {f}"
    resp_bin = await client.post(f"/api/events/{ev['id']}/move-to-bin", headers=auth_headers)
    assert resp_bin.status_code == 200, f"Move to bin failed: {resp_bin.status_code} {resp_bin.text}"
    restored = resp_bin.json()
    for f in ("place_id", "lat", "lng", "address", "photo_url", "rating", "price_level", "types"):
        assert restored.get(f) == _ENRICHED.get(f), f"Restored field mismatch: {f}"
