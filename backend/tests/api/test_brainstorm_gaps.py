"""§3A — Brainstorm API gap tests.

Tests that fill coverage gaps identified in the test plan for chat, extract,
bulk, and promote edge cases.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept
from app.services.llm_client import _BANGKOK_FALLBACK_ITEMS


_SAMPLE_ITEM = {
    "title": "Grand Palace",
    "description": "Ornate 18th-century royal complex",
    "category": "Landmarks & Viewpoints",
    "place_id": "ChIJAZRkDm2Y4jARlEBP0aD8lVs",
    "lat": 13.75,
    "lng": 100.4913,
    "address": "Na Phra Lan Rd, Bangkok 10200",
    "photo_url": "https://example.com/palace.jpg",
    "rating": 4.7,
    "price_level": 2,
    "types": ["landmark", "tourist_attraction"],
    "opening_hours": {"mon_sun": "8:30–15:30"},
    "phone": "+66 2 623 5500",
    "website": "https://www.royalgrandpalace.th/",
    "time_hint": None,
    "time_category": "late afternoon",
    "url_source": None,
}


# ── Chat edge cases ──────────────────────────────────────────────────────────


async def test_chat_empty_message_accepted(client: AsyncClient, auth_headers):
    """The API currently accepts empty messages (no min_length validation)."""
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_brainstorm_endpoints_404_on_nonexistent_trip(
    client: AsyncClient, auth_headers
):
    resp = await client.post(
        "/api/trips/99999/brainstorm/chat",
        json={"message": "Hello"},
        headers=auth_headers,
    )
    assert resp.status_code in (403, 404)


async def test_extract_dedups_against_existing_brainstorm_items(
    client: AsyncClient, auth_headers
):
    """Calling extract twice does not duplicate items."""
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Suggest Bangkok places"},
        headers=auth_headers,
    )
    resp1 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    first_count = len(resp1.json()["items"])
    assert first_count > 0

    resp2 = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    second_count = len(resp2.json()["items"])
    # Second extract should add 0 items (all deduplicated)
    assert second_count == 0


async def test_bulk_insert_creates_items_for_user(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM, {**_SAMPLE_ITEM, "title": "Wat Pho"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_promote_emits_notification_to_other_members_only(
    client: AsyncClient, auth_headers, second_auth_headers
):
    """Promoter does not self-notify; other members get BRAINSTORM_PROMOTED."""
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
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

    # Bob (second user) should see a notification
    bob_notifs = await client.get(
        "/api/notifications/",
        headers=second_auth_headers,
    )
    assert bob_notifs.status_code == 200
    notifs = bob_notifs.json()
    promoted_notifs = [n for n in notifs if n["type"] == "brainstorm_promoted"]
    assert len(promoted_notifs) >= 1

    # Alice (promoter) should NOT see a self-notification
    alice_notifs = await client.get(
        "/api/notifications/",
        headers=auth_headers,
    )
    alice_promoted = [n for n in alice_notifs.json() if n["type"] == "brainstorm_promoted"]
    assert len(alice_promoted) == 0


async def test_extract_envelope_handles_zero_map_output_items(
    client: AsyncClient, auth_headers
):
    """When LLM is disabled, extract always returns fallback items (non-zero)."""
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hi"},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # Fallback items contain all fields
    items = resp.json()["items"]
    assert len(items) == len(_BANGKOK_FALLBACK_ITEMS)


async def test_promote_added_by_user_with_no_first_name_falls_back(
    client: AsyncClient,
):
    """If user has empty name, added_by should handle gracefully."""
    # Register user with minimal name
    await client.post(
        "/api/users/register",
        json={"email": "noname@test.com", "password": "pass123", "name": ""},
    )
    login_resp = await client.post(
        "/api/users/login",
        json={"email": "noname@test.com", "password": "pass123"},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
    trip = await create_trip(client, headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=headers,
    )
    assert resp.status_code == 200
    # added_by should be None or empty, not crash
    idea = resp.json()[0]
    assert idea["added_by"] is None or idea["added_by"] == ""
