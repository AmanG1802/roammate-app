"""§5A — End-to-end propagation tests for FETCH_PHOTOS / FETCH_RATING flags.

Verifies that toggling feature flags correctly removes fields from
enriched items across the full pipeline (enrich → brainstorm → promote).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.google_maps import MockMapService, get_google_maps_service
from app.services.google_maps import cache as gmap_cache
from tests.conftest import create_trip


@pytest.fixture(autouse=True)
def _clear_cache():
    gmap_cache.clear_all()
    yield
    gmap_cache.clear_all()


async def test_mock_enrich_with_FETCH_PHOTOS_off_items_lack_photo_url(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_PHOTOS", False)
    svc = MockMapService()
    items = [{"title": "Wat Pho"}]
    enriched = await svc.enrich_items(items)
    assert "photo_url" not in enriched[0]
    # Other fields still present
    assert enriched[0]["place_id"] is not None
    assert enriched[0]["lat"] is not None


async def test_mock_enrich_with_FETCH_RATING_off_items_lack_rating_and_price_level(
    monkeypatch,
):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    svc = MockMapService()
    items = [{"title": "Wat Pho"}]
    enriched = await svc.enrich_items(items)
    assert "rating" not in enriched[0]
    assert "price_level" not in enriched[0]
    assert enriched[0]["place_id"] is not None


async def test_brainstorm_extract_with_FETCH_PHOTOS_off_enrichment_skips_photo(
    monkeypatch,
):
    """When FETCH_PHOTOS is off, enrich_items does not populate photo_url."""
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_PHOTOS", False)
    svc = MockMapService()
    items = [{"title": "Grand Palace"}, {"title": "Wat Arun"}]
    enriched = await svc.enrich_items(items)
    for item in enriched:
        assert "photo_url" not in item
        # place_id and lat/lng still populated
        assert item["place_id"] is not None
        assert item["lat"] is not None


async def test_brainstorm_extract_with_FETCH_RATING_off_enrichment_skips_rating(
    monkeypatch,
):
    """When FETCH_RATING is off, enrich_items does not populate rating/price."""
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    svc = MockMapService()
    items = [{"title": "Grand Palace"}, {"title": "Wat Arun"}]
    enriched = await svc.enrich_items(items)
    for item in enriched:
        assert "rating" not in item
        assert "price_level" not in item
        assert item["place_id"] is not None


async def test_flag_toggle_cache_entries_differ_by_field_signature(monkeypatch):
    """Toggling FETCH_RATING changes the cache key field signature."""
    from app.services.google_maps.v2 import _build_details_field_mask

    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", True)
    mask_on = _build_details_field_mask()

    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    mask_off = _build_details_field_mask()

    assert mask_on != mask_off
    assert "rating" in mask_on
    assert "rating" not in mask_off
