"""§8 Brainstorm Chat & Bin — chat, extract, bulk insert, promote, and visibility."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept
from app.services.llm_client import _BANGKOK_FALLBACK_ITEMS


_SAMPLE_ITEM = {
    "title": "Grand Palace",
    "description": "Royal complex",
    "category": "Landmarks & Viewpoints",
    "place_id": "ChIJAZRkDm2Y4jARlEBP0aD8lVs",
    "lat": 13.75,
    "lng": 100.4913,
    "address": "Na Phra Lan Rd, Bangkok 10200",
    "photo_url": "https://example.com/palace.jpg",
    "rating": 4.7,
    "price_level": 2,
    "types": ["landmark", "tourist_attraction"],
    "time_category": "late afternoon",
}


async def test_chat_returns_ai_response(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "What to do in Bangkok?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["assistant_message"]["content"]


async def test_chat_multi_turn_history_grows(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Q1"}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Q2"}, headers=auth_headers)
    msgs = (await client.get(f"/api/trips/{trip['id']}/brainstorm/messages", headers=auth_headers)).json()
    assert len(msgs) >= 4  # 2 user + 2 assistant


async def test_chat_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "X"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_extract_returns_structured_items(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bangkok ideas"}, headers=auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == len(_BANGKOK_FALLBACK_ITEMS)


async def test_extract_idempotent_no_duplicates(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bangkok"}, headers=auth_headers)
    r1 = await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)
    r2 = await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)
    assert len(r2.json()["items"]) == 0


async def test_bulk_insert_seeds_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    assert len(resp.json()) == 1


async def test_bulk_insert_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_bulk_insert_preserves_all_enriched_fields(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    item = resp.json()[0]
    assert item["place_id"] == _SAMPLE_ITEM["place_id"]
    assert item["lat"] == _SAMPLE_ITEM["lat"]
    assert item["lng"] == _SAMPLE_ITEM["lng"]


async def test_promote_items_to_idea_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)
    assert resp.status_code == 200
    ideas = resp.json()
    assert len(ideas) == 1
    idea_bin = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert len(idea_bin) >= 1


async def test_promote_same_item_twice_404(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    items = (await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)).json()
    item_id = items[0]["id"]
    r1 = await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": [item_id]}, headers=auth_headers)
    assert r1.status_code == 200
    r2 = await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": [item_id]}, headers=auth_headers)
    assert r2.status_code == 404


async def test_get_brainstorm_items(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_brainstorm_messages(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Hi"}, headers=auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}/brainstorm/messages", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_delete_all_brainstorm_items(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)
    resp = await client.delete(f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers)
    assert resp.status_code in (200, 204)
    remaining = (await client.get(f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers)).json()
    assert remaining == []


async def test_brainstorm_items_visible_only_to_owner(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)
    bob_items = (await client.get(f"/api/trips/{trip['id']}/brainstorm/items", headers=second_auth_headers)).json()
    assert bob_items == []
