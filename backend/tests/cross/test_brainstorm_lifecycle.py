"""End-to-end brainstorm lifecycle tests spanning multiple endpoints."""
import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept
from app.services.llm_client import _BANGKOK_FALLBACK_ITEMS
from app.core.time_categories import TIME_CATEGORY_DEFAULTS


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
    "opening_hours": {"mon_sun": "8:30–15:30"},
    "phone": "+66 2 623 5500",
    "website": "https://www.royalgrandpalace.th/",
    "time_hint": None,
    "time_category": "late afternoon",
    "url_source": None,
}


@pytest.mark.asyncio
async def test_chat_extract_promote_e2e(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)

    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "What to do in Bangkok?"},
        headers=auth_headers,
    )

    extract_resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    items = extract_resp.json()["items"]
    assert len(items) == len(_BANGKOK_FALLBACK_ITEMS)

    promote_resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    ideas = promote_resp.json()
    assert len(ideas) == len(_BANGKOK_FALLBACK_ITEMS)

    remaining = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers
    )).json()
    assert remaining == []

    idea_bin = (await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=auth_headers
    )).json()
    assert len(idea_bin) == len(_BANGKOK_FALLBACK_ITEMS)


@pytest.mark.asyncio
async def test_dashboard_plan_create_seed_e2e(client: AsyncClient, auth_headers):
    plan_resp = await client.post(
        "/api/llm/plan-trip",
        json={"prompt": "3-day Bangkok trip"},
        headers=auth_headers,
    )
    plan = plan_resp.json()
    assert plan["trip_name"] == "Thailand Getaway"

    trip = await create_trip(client, auth_headers, name=plan["trip_name"])

    bulk_resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": plan["items"]},
        headers=auth_headers,
    )
    assert len(bulk_resp.json()) == len(plan["items"])

    promote_resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    assert len(promote_resp.json()) == len(plan["items"])

    idea_bin = (await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=auth_headers
    )).json()
    assert len(idea_bin) == len(plan["items"])


@pytest.mark.asyncio
async def test_promote_then_vote(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    ideas = (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )).json()

    vote_resp = await client.post(
        f"/api/ideas/{ideas[0]['id']}/vote",
        json={"value": 1},
        headers=auth_headers,
    )
    assert vote_resp.status_code == 200
    assert vote_resp.json()["up"] == 1


@pytest.mark.asyncio
async def test_non_admin_promote_visible_in_shared_idea_bin(
    client: AsyncClient, auth_headers, second_auth_headers
):
    """A non-admin can promote from their brainstorm; the result is visible in the shared Idea Bin."""
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_only",
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=second_auth_headers,
    )
    ideas = (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=second_auth_headers,
    )).json()
    assert len(ideas) == 1
    assert ideas[0]["added_by"] == "Bob"

    alice_idea_bin = (await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=auth_headers
    )).json()
    assert any(i["title"] == "Grand Palace" for i in alice_idea_bin)

    bob_idea_bin = (await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=second_auth_headers
    )).json()
    assert any(i["title"] == "Grand Palace" for i in bob_idea_bin)


@pytest.mark.asyncio
async def test_two_users_independent_brainstorm(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
    )

    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Alice's question"},
        headers=auth_headers,
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Bob's question"},
        headers=second_auth_headers,
    )

    alice_msgs = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/messages", headers=auth_headers
    )).json()
    bob_msgs = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/messages", headers=second_auth_headers
    )).json()
    assert len(alice_msgs) == 2
    assert len(bob_msgs) == 2
    assert alice_msgs[0]["content"] == "Alice's question"
    assert bob_msgs[0]["content"] == "Bob's question"

    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [{**_SAMPLE_ITEM, "title": "Bob's Spot"}]},
        headers=second_auth_headers,
    )

    alice_items = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers
    )).json()
    bob_items = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=second_auth_headers
    )).json()
    assert len(alice_items) == 1
    assert len(bob_items) == 1
    assert alice_items[0]["title"] == "Grand Palace"
    assert bob_items[0]["title"] == "Bob's Spot"

    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )

    idea_bin = (await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=second_auth_headers
    )).json()
    assert any(i["title"] == "Grand Palace" for i in idea_bin)

    bob_items_after = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=second_auth_headers
    )).json()
    assert len(bob_items_after) == 1


@pytest.mark.asyncio
async def test_promoted_idea_appears_in_group_library(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    group = (await client.post(
        "/api/groups/", json={"name": "Travel Crew"}, headers=auth_headers
    )).json()
    attach = await client.post(
        f"/api/groups/{group['id']}/trips/{trip['id']}", headers=auth_headers
    )
    assert attach.status_code in (200, 201, 204)

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

    lib = (await client.get(
        f"/api/groups/{group['id']}/ideas", headers=auth_headers
    )).json()
    titles = [i["title"] for i in lib]
    assert "Grand Palace" in titles


@pytest.mark.asyncio
async def test_trip_delete_cascades_brainstorm(
    client: AsyncClient, auth_headers
):
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

    resp = await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code == 204

    items_resp = await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers
    )
    assert items_resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_promote_time_category_default_carries_to_idea(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    item_with_category = {
        **_SAMPLE_ITEM,
        "time_hint": None,
        "time_category": "evening",
    }
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [item_with_category]},
        headers=auth_headers,
    )
    ideas = (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )).json()

    assert ideas[0]["time_hint"] == TIME_CATEGORY_DEFAULTS["evening"]
    assert ideas[0]["time_category"] == "evening"
