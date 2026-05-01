"""§7D — Admin maps usage endpoint tests.

Seeds GoogleMapsApiUsage rows and verifies summary, filter, cache/error rates.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import GoogleMapsApiUsage


@pytest_asyncio.fixture
async def seed_maps_usage(db_session: AsyncSession):
    """Insert controllable GoogleMapsApiUsage rows for testing."""
    now = datetime.utcnow()
    rows = [
        GoogleMapsApiUsage(
            user_id=None, trip_id=None, op="find_place",
            status="ok", latency_ms=45, cache_state="miss",
            cost_usd=0.017, created_at=now,
        ),
        GoogleMapsApiUsage(
            user_id=None, trip_id=None, op="find_place",
            status="ok", latency_ms=1, cache_state="hit",
            cost_usd=0.0, created_at=now,
        ),
        GoogleMapsApiUsage(
            user_id=None, trip_id=None, op="place_details",
            status="ok", latency_ms=60, cache_state="miss",
            cost_usd=0.017, created_at=now,
        ),
        GoogleMapsApiUsage(
            user_id=None, trip_id=None, op="place_details",
            status="error", latency_ms=5000, cache_state=None,
            error_class="Timeout", cost_usd=0.017,
            created_at=now - timedelta(days=35),
        ),
        GoogleMapsApiUsage(
            user_id=None, trip_id=None, op="directions",
            status="ok", latency_ms=120, cache_state="miss",
            cost_usd=0.01, created_at=now,
        ),
    ]
    for row in rows:
        db_session.add(row)
    await db_session.commit()
    return rows


async def test_summary_no_filters(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    resp = await client.get("/api/admin/maps-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 5
    assert "cache_hits" in data
    assert "cache_hit_rate_pct" in data
    assert "error_count" in data
    assert "error_rate_pct" in data
    assert "total_cost_usd" in data
    assert "by_op" in data


async def test_summary_filter_by_ops_multi(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    resp = await client.get(
        "/api/admin/maps-usage/summary?ops=find_place&ops=directions",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 3  # 2 find_place + 1 directions


async def test_summary_filter_by_month(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    month_str = datetime.utcnow().strftime("%Y-%m")
    resp = await client.get(
        f"/api/admin/maps-usage/summary?month={month_str}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # 4 of 5 rows are this month (one is 35 days ago)
    assert data["total_calls"] == 4


async def test_summary_filter_by_day(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    resp = await client.get(
        f"/api/admin/maps-usage/summary?day={today}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] >= 3


async def test_summary_cache_hit_rate_calculation(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    resp = await client.get("/api/admin/maps-usage/summary", headers=admin_headers)
    data = resp.json()
    # 1 cache hit out of 5 total = 20%
    assert data["cache_hits"] == 1
    assert data["cache_hit_rate_pct"] == 20.0


async def test_summary_error_rate_calculation(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    resp = await client.get("/api/admin/maps-usage/summary", headers=admin_headers)
    data = resp.json()
    # 1 error out of 5 total = 20%
    assert data["error_count"] == 1
    assert data["error_rate_pct"] == 20.0


async def test_summary_zero_rows_returns_zero_rates_not_nan(
    client: AsyncClient, admin_headers
):
    resp = await client.get(
        "/api/admin/maps-usage/summary?ops=nonexistent_op",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 0
    assert data["cache_hit_rate_pct"] == 0
    assert data["error_rate_pct"] == 0
    assert data["total_cost_usd"] == 0


async def test_users_pivots_calls_by_op_per_user(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    resp = await client.get("/api/admin/maps-usage/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # All rows have user_id=None → single unattributed entry
    assert len(data) == 1
    assert data[0]["name"] == "Unattributed"
    assert "calls_by_op" in data[0]
    assert data[0]["calls_by_op"]["find_place"] == 2


async def test_users_total_cost_summed_per_user(
    client: AsyncClient, admin_headers, seed_maps_usage
):
    resp = await client.get("/api/admin/maps-usage/users", headers=admin_headers)
    data = resp.json()
    user = data[0]
    # Sum of all costs: 0.017 + 0.0 + 0.017 + 0.017 + 0.01 = 0.061
    assert user["cost_usd"] == pytest.approx(0.061, abs=0.001)
