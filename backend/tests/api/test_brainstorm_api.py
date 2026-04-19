"""Tests for brainstorm API endpoints (/api/trips/{id}/brainstorm/*)."""
import pytest
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept
from app.services.llm_client import _BANGKOK_FALLBACK_ITEMS
from app.core.time_categories import TIME_CATEGORY_DEFAULTS


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


# ── Chat ──────────────────────────────────────────────────────────────────────

async def test_chat_returns_assistant_message(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "What should I do in Bangkok?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant_message"]["role"] == "assistant"
    assert len(body["assistant_message"]["content"]) > 0
    assert len(body["history"]) == 2


async def test_chat_persists_messages(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hello"},
        headers=auth_headers,
    )
    resp = await client.get(
        f"/api/trips/{trip['id']}/brainstorm/messages",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


async def test_chat_multi_turn_history_grows(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Turn 1"},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Turn 2"},
        headers=auth_headers,
    )
    assert len(resp.json()["history"]) == 4


async def test_chat_non_member_403(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hi"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_chat_requires_auth_401(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hi"},
    )
    assert resp.status_code == 401


# ── Extract ───────────────────────────────────────────────────────────────────

async def test_extract_creates_brainstorm_items(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Suggest places"},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == len(_BANGKOK_FALLBACK_ITEMS)
    first = items[0]
    assert first["title"] == _BANGKOK_FALLBACK_ITEMS[0]["title"]
    assert first["description"] is not None
    assert first["lat"] is not None
    assert first["rating"] is not None


async def test_extract_items_have_added_by_ai(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Go"},
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=auth_headers,
    )
    for item in resp.json()["items"]:
        assert item["added_by"] == "AI"


async def test_extract_non_member_403(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/extract",
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


# ── Bulk insert ───────────────────────────────────────────────────────────────

async def test_bulk_insert_seeds_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Grand Palace"

    listed = await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items",
        headers=auth_headers,
    )
    assert len(listed.json()) == 1


async def test_bulk_insert_non_member_403(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


# ── List items ────────────────────────────────────────────────────────────────

async def test_list_items_returns_own_only(
    client: AsyncClient, auth_headers, second_auth_headers
):
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
    alice_items = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers
    )).json()
    bob_items = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=second_auth_headers
    )).json()
    assert len(alice_items) == 1
    assert len(bob_items) == 0


async def test_list_items_non_member_403(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items",
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


# ── List messages ─────────────────────────────────────────────────────────────

async def test_list_messages_returns_own_only(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hello"},
        headers=auth_headers,
    )
    alice_msgs = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/messages", headers=auth_headers
    )).json()
    bob_msgs = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/messages", headers=second_auth_headers
    )).json()
    assert len(alice_msgs) == 2
    assert len(bob_msgs) == 0


async def test_list_messages_non_member_403(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/trips/{trip['id']}/brainstorm/messages",
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


# ── Delete item ───────────────────────────────────────────────────────────────

async def test_delete_item_happy(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    items = (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )).json()
    resp = await client.delete(
        f"/api/trips/{trip['id']}/brainstorm/items/{items[0]['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 204


async def test_delete_item_nonexistent_404(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.delete(
        f"/api/trips/{trip['id']}/brainstorm/items/9999",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_delete_other_users_item_404(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
    )
    items = (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM]},
        headers=auth_headers,
    )).json()
    resp = await client.delete(
        f"/api/trips/{trip['id']}/brainstorm/items/{items[0]['id']}",
        headers=second_auth_headers,
    )
    assert resp.status_code == 404


# ── Clear all items ───────────────────────────────────────────────────────────

async def test_clear_items_deletes_all_for_user(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [_SAMPLE_ITEM, {**_SAMPLE_ITEM, "title": "Wat Pho"}]},
        headers=auth_headers,
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [{**_SAMPLE_ITEM, "title": "Bob's Place"}]},
        headers=second_auth_headers,
    )
    resp = await client.delete(
        f"/api/trips/{trip['id']}/brainstorm/items",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    alice_items = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers
    )).json()
    bob_items = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=second_auth_headers
    )).json()
    assert len(alice_items) == 0
    assert len(bob_items) == 1


# ── Promote ───────────────────────────────────────────────────────────────────

async def _seed_brainstorm(client, headers, trip_id, items=None):
    items = items or [_SAMPLE_ITEM]
    resp = await client.post(
        f"/api/trips/{trip_id}/brainstorm/bulk",
        json={"items": items},
        headers=headers,
    )
    return resp.json()


async def test_promote_all_moves_to_idea_bin(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _seed_brainstorm(client, auth_headers, trip["id"])

    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ideas = resp.json()
    assert len(ideas) == 1
    assert ideas[0]["title"] == "Grand Palace"

    remaining = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers
    )).json()
    assert len(remaining) == 0

    idea_bin = (await client.get(
        f"/api/trips/{trip['id']}/ideas", headers=auth_headers
    )).json()
    assert len(idea_bin) == 1


async def test_promote_subset(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    items = await _seed_brainstorm(
        client, auth_headers, trip["id"],
        items=[_SAMPLE_ITEM, {**_SAMPLE_ITEM, "title": "Wat Pho"}],
    )
    first_id = items[0]["id"]

    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": [first_id]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    remaining = (await client.get(
        f"/api/trips/{trip['id']}/brainstorm/items", headers=auth_headers
    )).json()
    assert len(remaining) == 1
    assert remaining[0]["title"] == "Wat Pho"


async def test_promote_full_field_copy(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _seed_brainstorm(client, auth_headers, trip["id"])

    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    idea = resp.json()[0]
    for field in (
        "title", "description", "category", "place_id", "lat", "lng",
        "address", "photo_url", "rating", "price_level", "types",
        "opening_hours", "phone", "website", "time_category", "url_source",
    ):
        assert idea[field] == _SAMPLE_ITEM[field], f"Field mismatch: {field}"


async def test_promote_added_by_is_promoter_not_ai(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    await _seed_brainstorm(client, auth_headers, trip["id"])

    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    idea = resp.json()[0]
    assert idea["added_by"] == "Alice"


async def test_promote_empty_ids_returns_empty(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_promote_nonexistent_ids_404(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _seed_brainstorm(client, auth_headers, trip["id"])
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": [9999]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_promote_other_users_item_404(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
    )
    items = await _seed_brainstorm(client, auth_headers, trip["id"])
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": [items[0]["id"]]},
        headers=second_auth_headers,
    )
    assert resp.status_code == 404


async def test_promote_non_member_403(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await _seed_brainstorm(client, auth_headers, trip["id"])
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_promote_time_category_populates_time_hint(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(client, auth_headers)
    item_no_hint = {
        **_SAMPLE_ITEM,
        "time_hint": None,
        "time_category": "morning",
    }
    await _seed_brainstorm(client, auth_headers, trip["id"], items=[item_no_hint])

    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )
    idea = resp.json()[0]
    assert idea["time_hint"] == TIME_CATEGORY_DEFAULTS["morning"]


# ── Role gating ───────────────────────────────────────────────────────────────

async def test_view_only_can_promote(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_only",
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [{**_SAMPLE_ITEM, "title": "Bob's item"}]},
        headers=second_auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=second_auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_view_with_vote_can_promote(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"],
        "bob@test.com", role="view_with_vote",
    )
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/bulk",
        json={"items": [{**_SAMPLE_ITEM, "title": "Bob's item"}]},
        headers=second_auth_headers,
    )
    resp = await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=second_auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── Voting after promotion ────────────────────────────────────────────────────

async def test_vote_works_on_promoted_idea(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _seed_brainstorm(client, auth_headers, trip["id"])
    promoted = (await client.post(
        f"/api/trips/{trip['id']}/brainstorm/promote",
        json={"item_ids": None},
        headers=auth_headers,
    )).json()

    idea_id = promoted[0]["id"]
    resp = await client.post(
        f"/api/ideas/{idea_id}/vote",
        json={"value": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["up"] == 1
    assert resp.json()["my_vote"] == 1
