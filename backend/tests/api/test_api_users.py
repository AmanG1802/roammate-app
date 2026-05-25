"""API tests for users.py — profile CRUD, personas catalog, account deletion."""

import pytest
from httpx import AsyncClient

NO_AUTH = {"Cookie": "", "Authorization": ""}


# ── GET /api/users/me ──────────────────────────────────────────────────────

async def test_get_me_get(client: AsyncClient, auth_headers: dict):
    # Test 1a - GET - 200 OK - Returns current user profile
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert data["name"] == "Alice Smith"
    assert "id" in data

    # Test 1b - GET - 401 Unauthorized - No auth header
    resp = await client.get("/api/users/me", headers=NO_AUTH)
    assert resp.status_code == 401


# ── PUT /api/users/me ──────────────────────────────────────────────────────

async def test_update_me_put(client: AsyncClient, auth_headers: dict):
    # Test 2a - PUT - 200 OK - Update name and travel_blurb
    resp = await client.put("/api/users/me", headers=auth_headers, json={
        "name": "Alice Updated", "travel_blurb": "Love mountains!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Alice Updated"
    assert data["travel_blurb"] == "Love mountains!"

    # Test 2b - PUT - 200 OK - Update timezone and currency
    resp = await client.put("/api/users/me", headers=auth_headers, json={
        "timezone": "Asia/Kolkata", "currency": "INR",
    })
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "Asia/Kolkata"

    # Test 2c - PUT - 400 Bad Request - Password change without current_password
    resp = await client.put("/api/users/me", headers=auth_headers, json={
        "password": "newpassword123",
    })
    assert resp.status_code == 400

    # Test 2d - PUT - 400 Bad Request - Password change with wrong current_password
    resp = await client.put("/api/users/me", headers=auth_headers, json={
        "password": "newpassword123", "current_password": "wrongpass",
    })
    assert resp.status_code == 400

    # Test 2e - PUT - 401 Unauthorized - No auth
    resp = await client.put("/api/users/me", json={"name": "Hacker"}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── GET /api/users/personas/catalog ────────────────────────────────────────

async def test_get_personas_catalog_get(client: AsyncClient, auth_headers: dict):
    # Test 3a - GET - 200 OK - Returns catalog list
    resp = await client.get("/api/users/personas/catalog", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── GET /api/users/me/personas ─────────────────────────────────────────────

async def test_get_my_personas_get(client: AsyncClient, auth_headers: dict):
    # Test 4a - GET - 200 OK - Returns user personas
    resp = await client.get("/api/users/me/personas", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "personas" in data

    # Test 4b - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/users/me/personas", headers=NO_AUTH)
    assert resp.status_code == 401


# ── PUT /api/users/me/personas ─────────────────────────────────────────────

async def test_update_my_personas_put(client: AsyncClient, auth_headers: dict):
    # Test 5a - PUT - 200 OK - Set valid personas
    catalog_resp = await client.get("/api/users/personas/catalog", headers=auth_headers)
    catalog = catalog_resp.json()
    if catalog:
        valid_slug = catalog[0]["value"] if isinstance(catalog[0], dict) and "value" in catalog[0] else catalog[0].get("slug", "")
        resp = await client.put("/api/users/me/personas", headers=auth_headers, json={
            "personas": [valid_slug] if valid_slug else [],
        })
        assert resp.status_code == 200

    # Test 5b - PUT - 422 Unprocessable Entity - Unknown persona slug
    resp = await client.put("/api/users/me/personas", headers=auth_headers, json={
        "personas": ["nonexistent_persona_xyz"],
    })
    assert resp.status_code == 422

    # Test 5c - PUT - 401 Unauthorized - No auth
    resp = await client.put("/api/users/me/personas", json={"personas": []}, headers=NO_AUTH)
    assert resp.status_code == 401


# ── DELETE /api/users/me ───────────────────────────────────────────────────

async def test_delete_me_delete(client: AsyncClient, auth_headers: dict):
    # Test 6a - DELETE - 200 OK - Account deletion
    resp = await client.delete("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "deleted" in data.get("detail", "").lower() or "deleted" in str(data).lower()

    # Test 6b - DELETE - 401 Unauthorized - No auth
    resp = await client.delete("/api/users/me", headers=NO_AUTH)
    assert resp.status_code == 401
