"""§2B — Persona catalog endpoint tests."""
from __future__ import annotations

from httpx import AsyncClient


async def test_GET_personas_catalog_returns_200(client: AsyncClient):
    resp = await client.get("/api/users/personas/catalog")
    assert resp.status_code == 200


async def test_GET_personas_catalog_returns_14_items(client: AsyncClient):
    resp = await client.get("/api/users/personas/catalog")
    data = resp.json()
    assert len(data) == 14


async def test_GET_personas_catalog_response_shape(client: AsyncClient):
    resp = await client.get("/api/users/personas/catalog")
    data = resp.json()
    for entry in data:
        assert "slug" in entry
        assert "label" in entry
        assert "icon" in entry
        assert "description" in entry


async def test_GET_personas_catalog_stable_order(client: AsyncClient):
    resp1 = await client.get("/api/users/personas/catalog")
    resp2 = await client.get("/api/users/personas/catalog")
    assert resp1.json() == resp2.json()
