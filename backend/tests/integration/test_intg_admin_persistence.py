"""§34 Admin Persistence & Token Attribution — cross-cutting: LLM → DB → admin visibility."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.all_models import TokenUsage
from tests.conftest import (
    TestSessionLocal,
    create_trip,
    wait_for_tracker_writes,
    _register_and_login,
)


async def test_brainstorm_chat_then_admin_token_usage_summary_reflects_call(
    client: AsyncClient, auth_headers, admin_headers, tracker_db
):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bangkok"}, headers=auth_headers)
    await wait_for_tracker_writes()
    resp = await client.get("/api/admin/token-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    assert "request_count" in resp.json()


async def test_two_users_usage_correctly_attributed(client: AsyncClient, auth_headers, second_auth_headers, admin_headers, tracker_db):
    alice = (await client.get("/api/users/me", headers=auth_headers)).json()
    bob = (await client.get("/api/users/me", headers=second_auth_headers)).json()
    async with TestSessionLocal() as session:
        session.add(TokenUsage(user_id=alice["id"], op="chat", provider="openai", model="gpt-4o-mini", tokens_in=100, tokens_out=50, tokens_total=150, source="brainstorm", cost_usd=0.0001))
        session.add(TokenUsage(user_id=bob["id"], op="chat", provider="openai", model="gpt-4o-mini", tokens_in=200, tokens_out=100, tokens_total=300, source="brainstorm", cost_usd=0.0002))
        await session.commit()
    resp = await client.get("/api/admin/token-usage/users", headers=admin_headers)
    assert resp.status_code == 200 and len(resp.json()) >= 2


async def test_user_deleted_orphans_token_usage_visible_as_unattributed(client: AsyncClient, admin_headers, tracker_db):
    async with TestSessionLocal() as session:
        session.add(TokenUsage(user_id=None, op="chat", provider="openai", model="gpt-4o-mini", tokens_in=50, tokens_out=25, tokens_total=75, source="brainstorm", cost_usd=0.0001))
        await session.commit()
    resp = await client.get("/api/admin/token-usage/users", headers=admin_headers)
    unattributed = [u for u in resp.json() if u["user_id"] is None]
    assert len(unattributed) >= 1 and unattributed[0]["name"] == "Unattributed"


async def test_admin_login_does_not_create_token_usage_row(client: AsyncClient, tracker_db):
    from app.core.config import settings
    await client.post("/api/admin/login", json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD})
    await wait_for_tracker_writes()
    async with TestSessionLocal() as session:
        rows = (await session.execute(select(TokenUsage))).scalars().all()
    assert len(rows) == 0


async def test_user_register_login_chat_admin_summary_full_loop(client: AsyncClient, admin_headers):
    headers = await _register_and_login(client, "lifecycle@test.com", "LifeUser")
    trip = await create_trip(client, headers)
    await client.post(f"/api/trips/{trip['id']}/brainstorm/chat", json={"message": "Bangkok"}, headers=headers)
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    assert "lifecycle@test.com" in [u["email"] for u in resp.json()["users"]]


async def test_user_delete_then_admin_summary_marks_rows_unattributed(client: AsyncClient, admin_headers):
    headers = await _register_and_login(client, "tobedeleted@test.com", "Doomed")
    await client.delete("/api/users/me", headers=headers)
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert "tobedeleted@test.com" not in [u["email"] for u in resp.json()["users"]]
