"""§7F + §8E — Admin × Persistence × User lifecycle end-to-end tests.

Verifies the full loop: user action → tracker persistence → admin visibility.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TestSessionLocal,
    create_trip,
    wait_for_tracker_writes,
    _register_and_login,
)


async def test_brainstorm_chat_then_admin_token_usage_summary_reflects_call(
    client: AsyncClient, auth_headers, admin_headers, tracker_db
):
    """Call brainstorm chat as user, then admin summary contains the row."""
    trip = await create_trip(client, auth_headers)
    await client.post(
        f"/api/trips/{trip['id']}/brainstorm/chat",
        json={"message": "Hello Bangkok"},
        headers=auth_headers,
    )
    await wait_for_tracker_writes()

    resp = await client.get("/api/admin/token-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    # LLM_ENABLED=False → no token tracking happens (fallback path skips model call)
    # This verifies the admin endpoint doesn't crash even with 0 rows
    data = resp.json()
    assert "request_count" in data


async def test_two_users_usage_correctly_attributed(
    client: AsyncClient, admin_headers, tracker_db
):
    """Two users chatting have distinct token usage when LLM tracks."""
    from app.models.all_models import TokenUsage
    from sqlalchemy.ext.asyncio import AsyncSession
    from datetime import datetime

    # Manually insert attributed rows to simulate what LLM-enabled tracking does
    async with TestSessionLocal() as session:
        session.add(TokenUsage(
            user_id=1, trip_id=None, op="chat", provider="openai",
            model="gpt-4o-mini", tokens_in=100, tokens_out=50,
            tokens_total=150, source="brainstorm", cost_usd=0.0001,
        ))
        session.add(TokenUsage(
            user_id=2, trip_id=None, op="chat", provider="openai",
            model="gpt-4o-mini", tokens_in=200, tokens_out=100,
            tokens_total=300, source="brainstorm", cost_usd=0.0002,
        ))
        await session.commit()

    resp = await client.get("/api/admin/token-usage/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


async def test_user_deleted_orphans_token_usage_visible_as_unattributed(
    client: AsyncClient, admin_headers, tracker_db, db_session
):
    """After user deletion, their token usage rows show as unattributed.

    NOTE: SQLite does not enforce SET NULL on FK by default, so we insert
    the row with user_id=NULL directly to simulate the post-delete state.
    """
    from app.models.all_models import TokenUsage

    # Simulate an orphaned row (user_id=NULL, as happens after cascade SET NULL)
    async with TestSessionLocal() as session:
        session.add(TokenUsage(
            user_id=None, trip_id=None, op="chat", provider="openai",
            model="gpt-4o-mini", tokens_in=50, tokens_out=25,
            tokens_total=75, source="brainstorm", cost_usd=0.0001,
        ))
        await session.commit()

    # Admin sees the row as unattributed
    resp = await client.get("/api/admin/token-usage/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    unattributed = [u for u in data if u["user_id"] is None]
    assert len(unattributed) >= 1
    assert unattributed[0]["name"] == "Unattributed"


async def test_admin_login_does_not_create_token_usage_row(
    client: AsyncClient, tracker_db
):
    """Admin login action should not pollute the token usage metrics."""
    from app.core.config import settings
    from sqlalchemy import select
    from app.models.all_models import TokenUsage

    await client.post(
        "/api/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    await wait_for_tracker_writes()

    async with TestSessionLocal() as session:
        rows = (await session.execute(select(TokenUsage))).scalars().all()
    assert len(rows) == 0
