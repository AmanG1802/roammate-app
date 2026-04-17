"""Tests for /api/users/*."""
import pytest
from datetime import timedelta
from httpx import AsyncClient
from app.core.security import create_access_token


async def test_register_returns_user_out(client: AsyncClient):
    resp = await client.post(
        "/api/users/register",
        json={"email": "a@b.com", "password": "pw123456", "name": "Alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "a@b.com"
    assert data["name"] == "Alice"
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@b.com", "password": "pw123456", "name": "A"}
    await client.post("/api/users/register", json=payload)
    resp = await client.post("/api/users/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/api/users/register",
        json={"email": "not-an-email", "password": "pw", "name": "A"},
    )
    assert resp.status_code == 422


async def test_register_missing_fields(client: AsyncClient):
    resp = await client.post("/api/users/register", json={"email": "a@b.com"})
    assert resp.status_code == 422


async def test_login_returns_bearer_token(client: AsyncClient):
    await client.post(
        "/api/users/register",
        json={"email": "l@b.com", "password": "pw123456", "name": "L"},
    )
    resp = await client.post(
        "/api/users/login", json={"email": "l@b.com", "password": "pw123456"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        "/api/users/login", json={"email": "nobody@b.com", "password": "pw"}
    )
    assert resp.status_code == 401


async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/users/register",
        json={"email": "wp@b.com", "password": "correct123", "name": "WP"},
    )
    resp = await client.post(
        "/api/users/login", json={"email": "wp@b.com", "password": "wrong123"}
    )
    assert resp.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, auth_headers):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@test.com"


async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_me_malformed_token(client: AsyncClient):
    resp = await client.get(
        "/api/users/me", headers={"Authorization": "Bearer garbage"}
    )
    assert resp.status_code == 401


async def test_me_expired_token(client: AsyncClient):
    token = create_access_token(subject=1, expires_delta=timedelta(seconds=-1))
    resp = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_me_token_for_deleted_user(client: AsyncClient):
    # Token references user id that never existed → 401
    token = create_access_token(subject=99999)
    resp = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
