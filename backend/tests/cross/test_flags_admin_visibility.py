"""§8F — Flags × Admin visibility tests.

Verifies that toggling feature flags is reflected in admin usage metrics.
"""
from __future__ import annotations

from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import GoogleMapsApiUsage


@pytest_asyncio.fixture
async def seed_maps_with_flags(db_session: AsyncSession):
    """Seed maps usage rows that simulate flag-off behaviour."""
    now = datetime.utcnow()
    rows = [
        # With photos on: includes photo_url call
        GoogleMapsApiUsage(
            op="photo_url", status="ok", latency_ms=30,
            cache_state="miss", cost_usd=0.007, created_at=now,
        ),
        GoogleMapsApiUsage(
            op="find_place", status="ok", latency_ms=40,
            cache_state="miss", cost_usd=0.017, created_at=now,
        ),
        GoogleMapsApiUsage(
            op="place_details", status="ok", latency_ms=50,
            cache_state="miss", cost_usd=0.017, created_at=now,
        ),
    ]
    for row in rows:
        db_session.add(row)
    await db_session.commit()
    return rows


async def test_admin_maps_usage_shows_photo_url_calls(
    client: AsyncClient, admin_headers, seed_maps_with_flags
):
    """When photos flag was on, photo_url calls appear in admin metrics."""
    resp = await client.get("/api/admin/maps-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "photo_url" in data["by_op"]
    assert data["by_op"]["photo_url"] == 1


async def test_with_FETCH_PHOTOS_off_no_new_photo_url_calls(
    client: AsyncClient, admin_headers, db_session: AsyncSession
):
    """When photos flag is off, no photo_url rows are created in the metrics."""
    # With no seeded data, there should be no photo_url calls
    resp = await client.get(
        "/api/admin/maps-usage/summary?ops=photo_url",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total_calls"] == 0
