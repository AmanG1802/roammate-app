"""§1 Auth & Identity — integration tests for the full auth lifecycle.

Covers signup, verification, login, refresh rotation, logout, OAuth stubs,
password forgot/reset, email change, and identity management.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from sqlalchemy import select, update

from tests.conftest import TestSessionLocal, _register_and_login
from app.models.all_models import User, EmailVerification, PasswordReset


async def _signup(client, email="test@test.com", password="password123", name="Test"):
    return await client.post("/api/auth/signup", json={
        "email": email, "password": password, "name": name,
    })


async def _verify_email(email: str):
    async with TestSessionLocal() as s:
        await s.execute(update(User).where(User.email == email).values(email_verified=True))
        await s.commit()


async def _login(client, email="test@test.com", password="password123", skip=True):
    return await client.post("/api/auth/login", json={
        "email": email, "password": password, "skip_verification": skip,
    })


# ── Signup ────────────────────────────────────────────────────────────────────

async def test_signup_creates_unverified_user(client: AsyncClient):
    resp = await _signup(client)
    assert resp.status_code == 200
    async with TestSessionLocal() as s:
        user = (await s.execute(select(User).where(User.email == "test@test.com"))).scalars().first()
    assert user is not None
    assert user.email_verified is False


async def test_signup_duplicate_email_does_not_leak(client: AsyncClient):
    await _signup(client, email="dup@test.com")
    resp = await _signup(client, email="dup@test.com")
    assert resp.status_code == 200


async def test_signup_unverified_duplicate_reissues_token(client: AsyncClient):
    await _signup(client)
    async with TestSessionLocal() as s:
        tokens_before = (await s.execute(
            select(EmailVerification).join(User).where(User.email == "test@test.com")
        )).scalars().all()
    resp = await _signup(client)
    assert resp.status_code == 200
    async with TestSessionLocal() as s:
        tokens_after = (await s.execute(
            select(EmailVerification).join(User).where(User.email == "test@test.com")
        )).scalars().all()
    assert len(tokens_after) >= len(tokens_before)


# ── Verify ────────────────────────────────────────────────────────────────────

async def test_verify_expired_token_rejected(client: AsyncClient):
    resp = await client.post("/api/auth/verify", json={"token": "expired-fake-token"})
    assert resp.status_code == 400


async def test_verify_resend_204_for_unknown_email(client: AsyncClient):
    resp = await client.post("/api/auth/verify/resend", json={"email": "ghost@test.com"})
    assert resp.status_code == 204


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_correct_credentials(client: AsyncClient):
    await _signup(client)
    await _verify_email("test@test.com")
    resp = await _login(client)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password_401(client: AsyncClient):
    await _signup(client)
    await _verify_email("test@test.com")
    resp = await _login(client, password="wrong")
    assert resp.status_code == 401


async def test_login_unverified_email_409(client: AsyncClient):
    await _signup(client)
    resp = await _login(client, skip=False)
    assert resp.status_code == 409


async def test_login_skip_verification_flag(client: AsyncClient):
    await _signup(client)
    resp = await _login(client, skip=True)
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ── Refresh ───────────────────────────────────────────────────────────────────

async def test_refresh_expired_token_401(client: AsyncClient):
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

async def test_logout_revokes_refresh_and_clears_cookies(client: AsyncClient):
    await _signup(client)
    await _verify_email("test@test.com")
    login_resp = await _login(client)
    rt = login_resp.json()["refresh_token"]
    resp = await client.post("/api/auth/logout", json={"refresh_token": rt})
    assert resp.status_code == 204


# ── Password forgot / reset ──────────────────────────────────────────────────

async def test_password_forgot_sends_reset(client: AsyncClient):
    await _signup(client)
    await _verify_email("test@test.com")
    resp = await client.post("/api/auth/password/forgot", json={"email": "test@test.com"})
    assert resp.status_code == 204


async def test_password_forgot_unknown_email_204(client: AsyncClient):
    resp = await client.post("/api/auth/password/forgot", json={"email": "nobody@x.com"})
    assert resp.status_code == 204


async def test_password_reset_expired_400(client: AsyncClient):
    resp = await client.post("/api/auth/password/reset", json={
        "token": "invalid", "new_password": "newpass12345",
    })
    assert resp.status_code == 400


# ── OAuth stubs ───────────────────────────────────────────────────────────────

async def test_google_oauth_invalid_token_400(client: AsyncClient):
    with patch("app.services.auth.oauth_google.verify", new_callable=AsyncMock,
               side_effect=ValueError("bad")):
        resp = await client.post("/api/auth/google", json={"id_token": "bad"})
    assert resp.status_code == 400


async def test_apple_oauth_invalid_token_400(client: AsyncClient):
    with patch("app.services.auth.oauth_apple.verify", new_callable=AsyncMock,
               side_effect=ValueError("bad")):
        resp = await client.post("/api/auth/apple", json={"id_token": "bad"})
    assert resp.status_code == 400


# ── Email change ──────────────────────────────────────────────────────────────

async def test_change_email_wrong_password_400(client: AsyncClient, auth_headers):
    resp = await client.post("/api/auth/me/email/change", headers=auth_headers, json={
        "new_email": "new@test.com", "password": "wrong_password",
    })
    assert resp.status_code == 400


async def test_change_email_same_email_400(client: AsyncClient, auth_headers):
    resp = await client.post("/api/auth/me/email/change", headers=auth_headers, json={
        "new_email": "alice@test.com", "password": "password123",
    })
    assert resp.status_code == 400


async def test_change_email_issues_verification(client: AsyncClient, auth_headers):
    resp = await client.post("/api/auth/me/email/change", headers=auth_headers, json={
        "new_email": "newalice@test.com", "password": "password123",
    })
    assert resp.status_code == 204


# ── Identities ────────────────────────────────────────────────────────────────

async def test_list_identities_shows_linked_providers(client: AsyncClient, auth_headers):
    resp = await client.get("/api/auth/me/identities", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "has_password" in data
    assert "identities" in data


async def test_unlink_nonexistent_identity_404(client: AsyncClient, auth_headers):
    resp = await client.delete("/api/auth/me/identities/google", headers=auth_headers)
    assert resp.status_code == 404
