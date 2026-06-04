"""§21 Admin Panel — login, JWT isolation, user listing, and usage summaries."""
from __future__ import annotations

from datetime import datetime

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.models.all_models import TokenUsage, GoogleMapsApiUsage
from tests.conftest import TestSessionLocal


async def test_admin_login_success(client: AsyncClient):
    resp = await client.post("/api/admin/login", json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_admin_login_wrong_credentials(client: AsyncClient):
    resp = await client.post("/api/admin/login", json={"username": "wrong", "password": "wrong"})
    assert resp.status_code == 401


async def test_admin_jwt_rejects_regular_user(client: AsyncClient, auth_headers):
    resp = await client.get("/api/admin/users", headers=auth_headers)
    assert resp.status_code == 403


async def test_admin_list_users(client: AsyncClient, admin_headers):
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    assert "users" in resp.json()


async def test_admin_token_usage_summary(client: AsyncClient, admin_headers):
    resp = await client.get("/api/admin/token-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    assert "request_count" in resp.json()


async def test_admin_token_usage_per_user(client: AsyncClient, auth_headers, admin_headers):
    me = (await client.get("/api/users/me", headers=auth_headers)).json()
    async with TestSessionLocal() as s:
        s.add(TokenUsage(user_id=me["id"], op="chat", provider="openai", model="gpt-4o-mini", tokens_in=100, tokens_out=50, tokens_total=150, source="brainstorm", cost_usd=0.0001))
        await s.commit()
    resp = await client.get("/api/admin/token-usage/users", headers=admin_headers)
    assert resp.status_code == 200


async def test_admin_token_usage_filter_options(client: AsyncClient, admin_headers):
    resp = await client.get("/api/admin/token-usage/options", headers=admin_headers)
    assert resp.status_code == 200


async def test_admin_maps_usage_summary(client: AsyncClient, admin_headers, db_session):
    async with TestSessionLocal() as s:
        s.add(GoogleMapsApiUsage(op="place_details_v1", status="ok", latency_ms=40, cache_state="miss", cost_usd=0.017, created_at=datetime.utcnow()))
        await s.commit()
    resp = await client.get("/api/admin/maps-usage/summary", headers=admin_headers)
    assert resp.status_code == 200


async def test_admin_maps_usage_per_user(client: AsyncClient, admin_headers):
    resp = await client.get("/api/admin/maps-usage/users", headers=admin_headers)
    assert resp.status_code == 200
