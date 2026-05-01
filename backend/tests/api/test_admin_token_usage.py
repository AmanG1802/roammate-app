"""§7C — Admin token usage endpoint tests.

Seeds TokenUsage rows via fixture and verifies summary, filter, and per-user views.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import TokenUsage
from tests.conftest import TestSessionLocal


@pytest_asyncio.fixture
async def seed_token_usage(db_session: AsyncSession):
    """Insert controllable TokenUsage rows for testing."""
    now = datetime.utcnow()
    rows = [
        TokenUsage(
            user_id=None, trip_id=None, op="chat",
            provider="openai", model="gpt-4o-mini",
            tokens_in=100, tokens_out=50, tokens_total=150,
            source="brainstorm", cost_usd=0.000075,
            created_at=now,
        ),
        TokenUsage(
            user_id=None, trip_id=None, op="extract",
            provider="openai", model="gpt-4o-mini",
            tokens_in=200, tokens_out=300, tokens_total=500,
            source="brainstorm", cost_usd=0.00021,
            created_at=now,
        ),
        TokenUsage(
            user_id=None, trip_id=None, op="chat",
            provider="claude", model="claude-sonnet-4-20250514",
            tokens_in=80, tokens_out=40, tokens_total=120,
            source="concierge", cost_usd=0.00084,
            created_at=now - timedelta(days=35),  # previous month
        ),
        TokenUsage(
            user_id=None, trip_id=None, op="plan_trip",
            provider="gemini", model="gemini-2.0-flash",
            tokens_in=500, tokens_out=1000, tokens_total=1500,
            source="plan_trip", cost_usd=0.000338,
            created_at=now - timedelta(days=1),
        ),
    ]
    for row in rows:
        db_session.add(row)
    await db_session.commit()
    return rows


async def test_summary_no_filters_returns_total_and_breakdowns(
    client: AsyncClient, admin_headers, seed_token_usage
):
    resp = await client.get("/api/admin/token-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tokens" in data
    assert "total_cost_usd" in data
    assert "request_count" in data
    assert "avg_tokens_per_request" in data
    assert "top_model" in data
    assert "by_provider" in data
    assert "by_model" in data
    assert data["request_count"] == 4
    assert data["total_tokens"] == 150 + 500 + 120 + 1500


async def test_summary_filter_by_provider(
    client: AsyncClient, admin_headers, seed_token_usage
):
    resp = await client.get(
        "/api/admin/token-usage/summary?provider=openai",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_count"] == 2
    assert "openai" in data["by_provider"]


async def test_summary_filter_by_model(
    client: AsyncClient, admin_headers, seed_token_usage
):
    resp = await client.get(
        "/api/admin/token-usage/summary?model=gpt-4o-mini",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_count"] == 2


async def test_summary_filter_by_month(
    client: AsyncClient, admin_headers, seed_token_usage
):
    now = datetime.utcnow()
    month_str = now.strftime("%Y-%m")
    resp = await client.get(
        f"/api/admin/token-usage/summary?month={month_str}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Only rows from this month (row 0, 1, 3 depending on day boundary)
    assert data["request_count"] >= 2


async def test_summary_filter_by_day(
    client: AsyncClient, admin_headers, seed_token_usage
):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    resp = await client.get(
        f"/api/admin/token-usage/summary?day={today}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_count"] >= 1


async def test_summary_invalid_month_format_silently_ignored(
    client: AsyncClient, admin_headers, seed_token_usage
):
    resp = await client.get(
        "/api/admin/token-usage/summary?month=not-a-month",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    # Returns all rows (filter ignored)
    assert resp.json()["request_count"] == 4


async def test_summary_avg_tokens_zero_when_no_rows(
    client: AsyncClient, admin_headers
):
    resp = await client.get(
        "/api/admin/token-usage/summary?provider=nonexistent",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["avg_tokens_per_request"] == 0
    assert data["request_count"] == 0


async def test_options_returns_distinct_provider_to_model_mapping(
    client: AsyncClient, admin_headers, seed_token_usage
):
    resp = await client.get("/api/admin/token-usage/options", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert "openai" in data["providers"]
    assert "gpt-4o-mini" in data["providers"]["openai"]


async def test_options_empty_when_no_token_usage_rows(
    client: AsyncClient, admin_headers
):
    resp = await client.get("/api/admin/token-usage/options", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["providers"] == {}


async def test_users_groups_by_user_and_sums_correctly(
    client: AsyncClient, admin_headers, seed_token_usage
):
    resp = await client.get("/api/admin/token-usage/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # All seeded rows have user_id=None → grouped as unattributed
    assert len(data) == 1
    assert data[0]["name"] == "Unattributed"
    assert data[0]["tokens_total"] == 150 + 500 + 120 + 1500
