"""§2C — GET/PUT /users/me/personas endpoint tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import _register_and_login


async def test_GET_my_personas_default_null(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/me/personas", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["personas"] is None


async def test_PUT_my_personas_happy_roundtrip(client: AsyncClient, auth_headers):
    resp = await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie", "nature_lover"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["personas"] == ["foodie", "nature_lover"]


async def test_PUT_my_personas_empty_list_explicit_skip(
    client: AsyncClient, auth_headers
):
    resp = await client.put(
        "/api/users/me/personas",
        json={"personas": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["personas"] == []


async def test_PUT_my_personas_unknown_slug_422(client: AsyncClient, auth_headers):
    resp = await client.put(
        "/api/users/me/personas",
        json={"personas": ["nonexistent_slug"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "nonexistent_slug" in resp.json()["detail"]


async def test_PUT_my_personas_partial_invalid_rejects_whole_request(
    client: AsyncClient, auth_headers
):
    # First set valid personas
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie"]},
        headers=auth_headers,
    )
    # Try to set mix of valid and invalid — should reject atomically
    resp = await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie", "INVALID_SLUG"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    # Original value unchanged
    get_resp = await client.get("/api/users/me/personas", headers=auth_headers)
    assert get_resp.json()["personas"] == ["foodie"]


async def test_PUT_my_personas_idempotent_same_value(
    client: AsyncClient, auth_headers
):
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie"]},
        headers=auth_headers,
    )
    resp = await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_PUT_my_personas_requires_auth_401(client: AsyncClient):
    resp = await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie"]},
    )
    assert resp.status_code == 401


async def test_PUT_my_personas_other_users_unaffected(
    client: AsyncClient, auth_headers, second_auth_headers
):
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie"]},
        headers=auth_headers,
    )
    bob_resp = await client.get("/api/users/me/personas", headers=second_auth_headers)
    assert bob_resp.json()["personas"] is None


async def test_GET_my_personas_after_update_reflects_change(
    client: AsyncClient, auth_headers
):
    await client.put(
        "/api/users/me/personas",
        json={"personas": ["nature_lover", "budget_hacker"]},
        headers=auth_headers,
    )
    resp = await client.get("/api/users/me/personas", headers=auth_headers)
    assert resp.json()["personas"] == ["nature_lover", "budget_hacker"]
