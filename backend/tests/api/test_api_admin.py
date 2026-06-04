"""API tests for admin.py — login, users, token-usage, maps-usage.

Admin auth is enforced via parameter-level ``Depends(get_admin)`` so the
guard survives spec_router re-registration.
"""

import pytest
from httpx import AsyncClient

NO_AUTH = {"Cookie": "", "Authorization": ""}


# ── POST /api/admin/login ──────────────────────────────────────────────────

async def test_admin_login_post(client: AsyncClient):
    from app.core.config import settings

    # Test 1a - POST - 200 OK - Valid admin credentials
    resp = await client.post("/api/admin/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test 1b - POST - 401 Unauthorized - Invalid credentials
    resp = await client.post("/api/admin/login", json={
        "username": "wrong", "password": "wrong",
    })
    assert resp.status_code == 401

    # Test 1c - POST - 422 Unprocessable Entity - Missing fields
    resp = await client.post("/api/admin/login", json={})
    assert resp.status_code == 422


# ── GET /api/admin/users ───────────────────────────────────────────────────

async def test_list_users_get(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    # Test 2a - GET - 200 OK - Admin can list users
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data

    # Test 2b - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/admin/users", headers=NO_AUTH)
    assert resp.status_code == 401

    # Test 2c - GET - 403 Forbidden - Regular user JWT (not admin token)
    resp = await client.get("/api/admin/users", headers=auth_headers)
    assert resp.status_code == 403


# ── GET /api/admin/token-usage/options ─────────────────────────────────────

async def test_token_usage_options_get(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    # Test 3a - GET - 200 OK - Admin gets token usage options
    resp = await client.get("/api/admin/token-usage/options", headers=admin_headers)
    assert resp.status_code == 200
    assert "providers" in resp.json()

    # Test 3b - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/admin/token-usage/options", headers=NO_AUTH)
    assert resp.status_code == 401

    # Test 3c - GET - 403 Forbidden - Regular user JWT
    resp = await client.get("/api/admin/token-usage/options", headers=auth_headers)
    assert resp.status_code == 403


# ── GET /api/admin/token-usage/summary ─────────────────────────────────────

async def test_token_usage_summary_get(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    # Test 4a - GET - 200 OK - Admin gets token usage summary
    resp = await client.get("/api/admin/token-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tokens" in data
    assert "request_count" in data

    # Test 4b - GET - 200 OK - With month filter
    resp = await client.get("/api/admin/token-usage/summary?month=2025-06", headers=admin_headers)
    assert resp.status_code == 200

    # Test 4c - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/admin/token-usage/summary", headers=NO_AUTH)
    assert resp.status_code == 401

    # Test 4d - GET - 403 Forbidden - Regular user JWT
    resp = await client.get("/api/admin/token-usage/summary", headers=auth_headers)
    assert resp.status_code == 403


# ── GET /api/admin/token-usage/users ───────────────────────────────────────

async def test_token_usage_users_get(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    # Test 5a - GET - 200 OK - Admin gets per-user token usage
    resp = await client.get("/api/admin/token-usage/users", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Test 5b - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/admin/token-usage/users", headers=NO_AUTH)
    assert resp.status_code == 401

    # Test 5c - GET - 403 Forbidden - Regular user JWT
    resp = await client.get("/api/admin/token-usage/users", headers=auth_headers)
    assert resp.status_code == 403


# ── GET /api/admin/maps-usage/summary ──────────────────────────────────────

async def test_maps_usage_summary_get(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    # Test 6a - GET - 200 OK - Admin gets maps usage summary
    resp = await client.get("/api/admin/maps-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_calls" in data

    # Test 6b - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/admin/maps-usage/summary", headers=NO_AUTH)
    assert resp.status_code == 401

    # Test 6c - GET - 403 Forbidden - Regular user JWT
    resp = await client.get("/api/admin/maps-usage/summary", headers=auth_headers)
    assert resp.status_code == 403


# ── GET /api/admin/maps-usage/users ────────────────────────────────────────

async def test_maps_usage_users_get(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    # Test 7a - GET - 200 OK - Admin gets per-user maps usage
    resp = await client.get("/api/admin/maps-usage/users", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Test 7b - GET - 401 Unauthorized - No auth
    resp = await client.get("/api/admin/maps-usage/users", headers=NO_AUTH)
    assert resp.status_code == 401

    # Test 7c - GET - 403 Forbidden - Regular user JWT
    resp = await client.get("/api/admin/maps-usage/users", headers=auth_headers)
    assert resp.status_code == 403
