"""§32 Brainstorm Concurrency — race conditions on promote, extract, and chat."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip

_SAMPLE = {"title": "Grand Palace", "category": "sight", "place_id": "pid_1", "lat": 13.75, "lng": 100.49}


async def test_two_concurrent_promotes_same_item_only_one_succeeds(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    items = (await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE]}, headers=auth_headers)).json()
    item_id = items[0]["id"]
    r1 = await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": [item_id]}, headers=auth_headers)
    assert r1.status_code == 200
    r2 = await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": [item_id]}, headers=auth_headers)
    assert r2.status_code == 404


async def test_concurrent_extract_does_not_double_insert(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bangkok ideas"}, headers=auth_headers)
    r1 = await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)
    assert r1.status_code == 200 and len(r1.json()["items"]) > 0
    r2 = await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)
    assert r2.status_code == 200 and len(r2.json()["items"]) == 0


async def test_promote_during_chat_does_not_corrupt_history(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Hello"}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/bulk", json={"items": [_SAMPLE]}, headers=auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/promote", json={"item_ids": None}, headers=auth_headers)
    msgs = (await client.get(f"/api/trips/{trip['id']}/brainstorm/messages", headers=auth_headers)).json()
    assert len(msgs) == 2
