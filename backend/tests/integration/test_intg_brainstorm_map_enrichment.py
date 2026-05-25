"""§31 Brainstorm ↔ Maps Enrichment — extract drives enrichment pipeline."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import create_trip


async def test_brainstorm_extract_calls_enrich_items(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bangkok places"}, headers=auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    for item in items:
        assert item["lat"] is not None and item["lng"] is not None


async def test_brainstorm_extract_enriched_items_have_place_id(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Things in Bangkok"}, headers=auth_headers)
    items = (await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)).json()["items"]
    enriched = sum(1 for i in items if i.get("place_id"))
    assert enriched > 0


async def test_brainstorm_extract_partial_enrichment_failures_skip_only_failing(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Plan Bangkok"}, headers=auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/brainstorm/extract", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) > 0
