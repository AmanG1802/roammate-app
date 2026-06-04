"""§30 Maps Feature-Flag Propagation — FETCH_PHOTOS / FETCH_RATING end-to-end."""
from __future__ import annotations

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import GoogleMapsApiUsage
from app.services.google_maps import MockMapService
from app.services.google_maps import cache as gmap_cache


@pytest.fixture(autouse=True)
def _clear():
    gmap_cache.clear_all()
    yield
    gmap_cache.clear_all()


async def test_mock_enrich_FETCH_PHOTOS_off_items_lack_photo_url(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_PHOTOS", False)
    svc = MockMapService()
    enriched = await svc.enrich_items([{"title": "Wat Pho"}])
    assert "photo_url" not in enriched[0]
    assert enriched[0]["place_id"] is not None


async def test_mock_enrich_FETCH_RATING_off_items_lack_rating_and_price_level(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    svc = MockMapService()
    enriched = await svc.enrich_items([{"title": "Wat Pho"}])
    assert "rating" not in enriched[0] and "price_level" not in enriched[0]


async def test_flag_toggle_cache_entries_differ_by_field_signature(monkeypatch):
    from app.services.google_maps.v2 import _build_details_field_mask
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", True)
    mask_on = _build_details_field_mask()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    mask_off = _build_details_field_mask()
    assert mask_on != mask_off and "rating" in mask_on and "rating" not in mask_off


async def test_admin_maps_usage_shows_photo_url_calls(client: AsyncClient, admin_headers, db_session: AsyncSession):
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as s:
        s.add(GoogleMapsApiUsage(op="photo_url", status="ok", latency_ms=30, cache_state="miss", cost_usd=0.007, created_at=datetime.utcnow()))
        s.add(GoogleMapsApiUsage(op="place_details_v1", status="ok", latency_ms=40, cache_state="miss", cost_usd=0.017, created_at=datetime.utcnow()))
        await s.commit()
    resp = await client.get("/api/admin/maps-usage/summary", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["by_op"]["photo_url"] == 1


async def test_FETCH_PHOTOS_off_no_new_photo_url_calls(client: AsyncClient, admin_headers):
    resp = await client.get("/api/admin/maps-usage/summary?ops=photo_url", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total_calls"] == 0
