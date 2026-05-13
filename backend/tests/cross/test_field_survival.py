"""Tests that all 13 PLACE_FIELDS + start_time/end_time survive promotions and round-trips.

- Cross-trip copy: enriched idea → copy to another trip → all fields intact.
- Round-trip: idea → timeline item → bin → timeline item → all fields intact.
"""
import pytest
from httpx import AsyncClient

from tests.conftest import create_trip
from app.models.all_models import PLACE_FIELDS


_ENRICHED_BRAINSTORM_ITEM = {
    "title": "Trevi Fountain",
    "description": "Iconic Baroque fountain",
    "category": "Culture & Arts",
    "place_id": "ChIJ1UCDJ1NgLxMRtrsCzOHxdvY",
    "lat": 41.9009,
    "lng": 12.4833,
    "address": "Piazza di Trevi, 00187 Roma RM, Italy",
    "photo_url": "https://maps.example.com/photo/trevi.jpg",
    "rating": 4.7,
    "price_level": 0,
    "types": ["tourist_attraction", "point_of_interest"],
    "time_category": "morning",
    "added_by": "AI",
}


# ── Cross-trip copy preserves all PLACE_FIELDS + time fields ─────────────────


@pytest.mark.asyncio
async def test_cross_trip_copy_preserves_all_place_fields(
    client: AsyncClient, auth_headers
):
    src_trip = await create_trip(client, auth_headers, name="Rome")
    dst_trip = await create_trip(client, auth_headers, name="Florence")

    seeded = (await client.post(
        f"/api/trips/{src_trip['id']}/brainstorm/bulk",
        json={"items": [_ENRICHED_BRAINSTORM_ITEM]},
        headers=auth_headers,
    )).json()

    ideas = (await client.post(
        f"/api/trips/{src_trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )).json()
    idea = ideas[0]

    await client.patch(
        f"/api/trips/{src_trip['id']}/ideas/{idea['id']}",
        json={"start_time": "2026-06-01T10:00:00Z"},
        headers=auth_headers,
    )

    copy_resp = await client.post(
        f"/api/ideas/{idea['id']}/copy",
        json={"target_trip_id": dst_trip["id"]},
        headers=auth_headers,
    )
    assert copy_resp.status_code == 200
    copy = copy_resp.json()

    for field in PLACE_FIELDS:
        if field == "added_by":
            continue
        assert copy[field] == _ENRICHED_BRAINSTORM_ITEM.get(field), f"Field mismatch: {field}"

    assert copy["start_time"] is not None


# ── Round-trip: idea → timeline → bin → timeline ─────────────────────────────


@pytest.mark.asyncio
async def test_idea_timeline_bin_timeline_round_trip(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers, start_date="2026-06-01T00:00:00")

    (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_ENRICHED_BRAINSTORM_ITEM]},
        headers=auth_headers,
    ))
    ideas = (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )).json()
    idea_id = ideas[0]["id"]

    event_resp = await client.post(
        "/api/events/",
        json={
            "trip_id": trip["id"],
            "source_idea_id": idea_id,
            "title": ideas[0]["title"],
            "day_date": "2026-06-01",
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
        headers=auth_headers,
    )
    assert event_resp.status_code == 201
    event = event_resp.json()

    for field in ("place_id", "lat", "lng", "address", "photo_url", "rating",
                   "price_level", "types", "time_category", "description", "category"):
        assert event[field] == _ENRICHED_BRAINSTORM_ITEM.get(field), \
            f"Event field mismatch: {field}"

    await client.delete(
        f"/api/trips/{trip['id']}/ideas/{idea_id}",
        headers=auth_headers,
    )

    bin_resp = await client.post(
        f"/api/events/{event['id']}/move-to-bin",
        headers=auth_headers,
    )
    assert bin_resp.status_code == 200
    restored_idea = bin_resp.json()

    for field in ("place_id", "lat", "lng", "address", "photo_url", "rating",
                   "price_level", "types", "time_category", "description", "category"):
        assert restored_idea[field] == _ENRICHED_BRAINSTORM_ITEM.get(field), \
            f"Restored idea field mismatch: {field}"
    assert restored_idea["start_time"] is not None
    assert restored_idea["end_time"] is not None

    event2_resp = await client.post(
        "/api/events/",
        json={
            "trip_id": trip["id"],
            "source_idea_id": restored_idea["id"],
            "title": restored_idea["title"],
            "day_date": "2026-06-01",
            "start_time": "2026-06-01T10:00:00",
            "end_time": "2026-06-01T11:00:00",
        },
        headers=auth_headers,
    )
    assert event2_resp.status_code == 201
    event2 = event2_resp.json()

    for field in ("place_id", "lat", "lng", "address", "photo_url", "rating",
                   "price_level", "types", "time_category", "description", "category"):
        assert event2[field] == _ENRICHED_BRAINSTORM_ITEM.get(field), \
            f"Second event field mismatch: {field}"
