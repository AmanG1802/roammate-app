"""§7A — Admin authentication tests.

Verifies login, JWT claims, expiry, and rejection of invalid tokens.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.core.security import ALGORITHM


async def test_login_correct_creds_returns_token(client: AsyncClient):
    resp = await client.post(
        "/api/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Verify token has admin claim
    payload = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["admin"] is True


async def test_login_wrong_username_401(client: AsyncClient):
    resp = await client.post(
        "/api/admin/login",
        json={"username": "wrong_user", "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 401


async def test_login_wrong_password_401(client: AsyncClient):
    resp = await client.post(
        "/api/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": "wrong_pass"},
    )
    assert resp.status_code == 401


async def test_login_returns_token_expiring_in_configured_hours(client: AsyncClient):
    resp = await client.post(
        "/api/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    token = resp.json()["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    exp = datetime.utcfromtimestamp(payload["exp"])
    # Should expire within ADMIN_TOKEN_EXPIRE_HOURS (+/- 1 minute tolerance)
    expected = datetime.utcnow() + timedelta(hours=settings.ADMIN_TOKEN_EXPIRE_HOURS)
    assert abs((exp - expected).total_seconds()) < 60


async def test_admin_endpoint_without_token_401(client: AsyncClient):
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 401


async def test_admin_endpoint_with_user_jwt_403(
    client: AsyncClient, auth_headers
):
    """Regular user JWT (no admin claim) gets 403."""
    resp = await client.get("/api/admin/users", headers=auth_headers)
    assert resp.status_code == 403


async def test_admin_endpoint_with_expired_admin_token_401(client: AsyncClient):
    expired = datetime.utcnow() - timedelta(hours=1)
    token = jwt.encode(
        {"admin": True, "exp": expired},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_admin_endpoint_with_token_signed_by_other_secret_401(
    client: AsyncClient,
):
    expire = datetime.utcnow() + timedelta(hours=4)
    token = jwt.encode(
        {"admin": True, "exp": expire},
        "totally-different-secret-key",
        algorithm=ALGORITHM,
    )
    resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


async def test_admin_endpoint_with_garbage_token_401(client: AsyncClient):
    resp = await client.get(
        "/api/admin/users",
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    assert resp.status_code == 401
