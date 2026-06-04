"""§19 Users & Personas — profile CRUD, persona catalog, and persona selection."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_get_profile(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@test.com"


async def test_update_profile(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me", json={"name": "Alice Updated"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice Updated"


async def test_update_profile_partial(client: AsyncClient, auth_headers):
    await client.put("/api/users/me", json={"name": "Orig", "travel_blurb": "Love it"}, headers=auth_headers)
    resp = await client.put("/api/users/me", json={"name": "NewName"}, headers=auth_headers)
    assert resp.json()["name"] == "NewName"


async def test_delete_account(client: AsyncClient, auth_headers):
    resp = await client.delete("/api/users/me", headers=auth_headers)
    assert resp.status_code in (200, 204)


async def test_persona_catalog_endpoint(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/personas/catalog", headers=auth_headers)
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 1
    assert "label" in catalog[0]


async def test_get_user_personas(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/me/personas", headers=auth_headers)
    assert resp.status_code == 200


async def test_set_user_personas(client: AsyncClient, auth_headers):
    resp = await client.put("/api/users/me/personas", json={"personas": ["foodie", "nature_lover"]}, headers=auth_headers)
    assert resp.status_code == 200
