"""§2D — Profile fields (PUT /users/me) tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import _register_and_login


async def test_PUT_me_updates_name_only_other_fields_unchanged(
    client: AsyncClient, auth_headers
):
    resp = await client.put(
        "/api/users/me",
        json={"name": "Alice Updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice Updated"
    assert resp.json()["email"] == "alice@test.com"


async def test_PUT_me_updates_home_city_timezone_currency_blurb(
    client: AsyncClient, auth_headers
):
    resp = await client.put(
        "/api/users/me",
        json={
            "home_city": "Bangkok",
            "timezone": "Asia/Bangkok",
            "currency": "THB",
            "travel_blurb": "Love exploring temples!",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["home_city"] == "Bangkok"
    assert data["timezone"] == "Asia/Bangkok"
    assert data["currency"] == "THB"
    assert data["travel_blurb"] == "Love exploring temples!"


async def test_PUT_me_password_requires_current_password_400(
    client: AsyncClient, auth_headers
):
    resp = await client.put(
        "/api/users/me",
        json={"password": "newpass123"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "current password" in resp.json()["detail"].lower()


async def test_PUT_me_password_wrong_current_400(
    client: AsyncClient, auth_headers
):
    resp = await client.put(
        "/api/users/me",
        json={"password": "newpass123", "current_password": "wrong_password"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


async def test_PUT_me_password_success_can_login_with_new_password(
    client: AsyncClient, auth_headers
):
    resp = await client.put(
        "/api/users/me",
        json={"password": "newpass456", "current_password": "password123"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Login with new password works
    login_resp = await client.post(
        "/api/users/login",
        json={"email": "alice@test.com", "password": "newpass456"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


async def test_PUT_me_password_old_password_no_longer_valid(
    client: AsyncClient, auth_headers
):
    await client.put(
        "/api/users/me",
        json={"password": "newpass789", "current_password": "password123"},
        headers=auth_headers,
    )
    login_resp = await client.post(
        "/api/users/login",
        json={"email": "alice@test.com", "password": "password123"},
    )
    assert login_resp.status_code == 401


async def test_PUT_me_avatar_url_accepts_values(
    client: AsyncClient, auth_headers
):
    resp = await client.put(
        "/api/users/me",
        json={"avatar_url": "/uploads/avatar.jpg"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] == "/uploads/avatar.jpg"


async def test_PUT_me_unauthenticated_401(client: AsyncClient):
    resp = await client.put(
        "/api/users/me",
        json={"name": "Hack"},
    )
    assert resp.status_code == 401


async def test_DELETE_me_removes_user(client: AsyncClient, auth_headers):
    resp = await client.delete("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Account deleted"

    # Can no longer access protected endpoints
    me_resp = await client.get("/api/users/me", headers=auth_headers)
    assert me_resp.status_code == 401


async def test_register_returns_personas_null(client: AsyncClient):
    resp = await client.post(
        "/api/users/register",
        json={"email": "fresh@test.com", "password": "pass123", "name": "Fresh"},
    )
    assert resp.status_code == 200
    assert resp.json()["personas"] is None


async def test_register_then_PUT_personas_then_GET_me_reflects_value(
    client: AsyncClient,
):
    await client.post(
        "/api/users/register",
        json={"email": "flow@test.com", "password": "pass123", "name": "Flow"},
    )
    login_resp = await client.post(
        "/api/users/login",
        json={"email": "flow@test.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        "/api/users/me/personas",
        json={"personas": ["foodie", "budget_hacker"]},
        headers=headers,
    )
    me_resp = await client.get("/api/users/me", headers=headers)
    assert me_resp.json()["personas"] == ["foodie", "budget_hacker"]
