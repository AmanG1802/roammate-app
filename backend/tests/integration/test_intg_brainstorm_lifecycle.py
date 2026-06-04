"""§8 Brainstorm Lifecycle — end-to-end flows spanning chat, extract, promote,
group library, and dashboard seeding.
"""
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


async def test_chat_to_extract_to_promote_full_flow(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bangkok?"}, headers=auth_headers)
    items = (await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)).json()["items"]
    assert len(items) == len(_BANGKOK_FALLBACK_ITEMS)
    ideas = (await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)).json()
    assert len(ideas) == len(_BANGKOK_FALLBACK_ITEMS)
    remaining = (await client.get(f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers)).json()
    assert remaining == []
    idea_bin = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert len(idea_bin) == len(_BANGKOK_FALLBACK_ITEMS)


async def test_promoted_ideas_surface_in_group_library(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    g_resp = await client.post("/api/groups", json={"name": "Crew"}, headers=auth_headers)
    assert g_resp.status_code == 201, f"Group create failed: {g_resp.status_code} {g_resp.text}"
    group = g_resp.json()
    await client.post(f"/api/groups/{group['id']}/trips/{trip['id']}", headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)
    lib = (await client.get(f"/api/groups/{group['id']}/ideas", headers=auth_headers)).json()
    assert any(i["title"] == "Grand Palace" for i in lib)


async def test_dashboard_plan_create_seed_e2e(client: AsyncClient, auth_headers):
    plan = (await client.post("/api/llm/plan-trip", json={"prompt": "3-day Bangkok"}, headers=auth_headers)).json()
    assert plan["trip_name"] == "Thailand Getaway"
    trip = await create_trip(client, auth_headers, name=plan["trip_name"])
    bulk = (await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": plan["items"]}, headers=auth_headers)).json()
    assert len(bulk) == len(plan["items"])
    ideas = (await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)).json()
    assert len(ideas) == len(plan["items"])


async def test_promote_then_vote(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)
    ideas = (await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)).json()
    resp = await client.post(f"/api/ideas/{ideas[0]['id']}/vote", json={"value": 1}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["up"] == 1


async def test_promote_time_category_carries_to_idea(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    item = {**_SAMPLE_ITEM, "time_category": "evening"}
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [item]}, headers=auth_headers)
    ideas = (await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)).json()
    assert ideas[0]["time_category"] == "evening"


async def test_non_admin_promote_visible_in_shared_idea_bin(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", role="view_only")
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=second_auth_headers)
    ideas = (await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=second_auth_headers)).json()
    assert len(ideas) == 1
    alice_ideas = (await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)).json()
    assert any(i["title"] == "Grand Palace" for i in alice_ideas)


async def test_two_users_independent_brainstorm(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com", role="view_with_vote")
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Alice Q"}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bob Q"}, headers=second_auth_headers)
    alice_msgs = (await client.get(f"/api/trips/{trip['id']}/brainstorm/messages", headers=auth_headers)).json()
    bob_msgs = (await client.get(f"/api/trips/{trip['id']}/brainstorm/messages", headers=second_auth_headers)).json()
    assert len(alice_msgs) == 2
    assert len(bob_msgs) == 2
    assert alice_msgs[0]["content"] == "Alice Q"
    assert bob_msgs[0]["content"] == "Bob Q"


async def test_trip_delete_cascades_brainstorm(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Hello"}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE_ITEM]}, headers=auth_headers)
    assert (await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)).status_code == 204
    resp = await client.get(f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers)
    assert resp.status_code in (403, 404)
