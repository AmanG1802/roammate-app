"""
Tests for /api/users/* endpoints:
  POST /register
  POST /login
  GET  /me
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/api/users/register",
        json={"email": "new@test.com", "password": "secret123", "name": "New User"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "new@test.com"
    assert body["name"] == "New User"
    assert "id" in body
    assert "hashed_password" not in body  # never leak the hash


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@test.com", "password": "pass", "name": "Dup"}
    await client.post("/api/users/register", json=payload)
    resp = await client.post("/api/users/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/api/users/register",
        json={"email": "not-an-email", "password": "pass", "name": "Bad"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/users/register",
        json={"email": "login@test.com", "password": "pass123", "name": "Login User"},
    )
    resp = await client.post(
        "/api/users/login",
        json={"email": "login@test.com", "password": "pass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/users/register",
        json={"email": "wp@test.com", "password": "correct", "name": "User"},
    )
    resp = await client.post(
        "/api/users/login",
        json={"email": "wp@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        "/api/users/login",
        json={"email": "ghost@test.com", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "user@test.com"
    assert body["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 401
