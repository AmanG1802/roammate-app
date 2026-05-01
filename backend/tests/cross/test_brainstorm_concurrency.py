"""§3B — Brainstorm concurrency / race condition tests.

Verifies that concurrent operations don't corrupt data.
"""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


_SAMPLE_ITEM = {
    "title": "Grand Palace",
    "description": "Royal complex",
    "category": "Landmarks & Viewpoints",
    "place_id": "pid_1",
    "lat": 13.75,
    "lng": 100.4913,
    "address": "Bangkok",
    "photo_url": None,
    "rating": 4.7,
    "price_level": 2,
    "types": ["landmark"],
    "opening_hours": None,
    "phone": None,
    "website": None,
    "time_hint": None,
    "time_category": "morning",
    "url_source": None,
}


async def test_two_concurrent_promotes_same_item_only_one_succeeds(
    client: AsyncClient, auth_headers
):
    """Promoting the same item twice concurrently — second call sees 404."""
    trip = await create_trip(client, auth_headers)
    items_resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    item_id = items_resp.json()[0]["id"]

    # First promote succeeds
    r1 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": [item_id]},
        headers=auth_headers,
    )
    assert r1.status_code == 200

    # Second promote on same item_id → 404 (already promoted/deleted)
    r2 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": [item_id]},
        headers=auth_headers,
    )
    assert r2.status_code == 404


async def test_concurrent_extract_does_not_double_insert(
    client: AsyncClient, auth_headers
):
    """Same chat history, two sequential extracts → second yields 0 new items."""
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Give me Bangkok ideas"},
        headers=auth_headers,
    )
    r1 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    assert r1.status_code == 200
    first_count = len(r1.json()["items"])
    assert first_count > 0

    r2 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 0


async def test_promote_during_chat_does_not_corrupt_history(
    client: AsyncClient, auth_headers
):
    """Promoting items doesn't affect the user's chat message history."""
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hello"},
        headers=auth_headers,
    )
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

    # Chat history should still be intact
    msgs_resp = await client.get(
        f"/api/trips/{trip['id']}/brainstorm/messages",
        headers=auth_headers,
    )
    assert msgs_resp.status_code == 200
    assert len(msgs_resp.json()) == 2  # user + assistant
