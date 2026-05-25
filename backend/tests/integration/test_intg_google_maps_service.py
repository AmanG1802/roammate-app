"""§23 Google Maps Service — v1, v2, mock, factory, and feature-flag behaviour."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.google_maps import (
    MockMapService, MockGoogleMapsService, RoutePoint, get_google_maps_service,
)
from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.breaker import breaker
from app.services.google_maps.v1 import MapServiceV1
from app.services.google_maps.v2 import MapServiceV2


@pytest.fixture(autouse=True)
async def _reset():
    gmap_cache.clear_all()
    breaker._state.failure_times.clear()
    breaker._state.opened_at = None
    breaker._state.half_open = False
    yield


def _fake_response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    resp.json.return_value = payload
    return resp


def _patched_client(resp):
    c = MagicMock()
    c.__aenter__ = AsyncMock(return_value=c)
    c.__aexit__ = AsyncMock(return_value=None)
    c.request = AsyncMock(return_value=resp)
    return c


# ── Mock ──────────────────────────────────────────────────────────────────────

async def test_mock_find_place_returns_full_shape():
    svc = MockMapService()
    r = await svc.find_place("Colosseum")
    assert r is not None and r["id"].startswith("mock_id_")


async def test_mock_directions_builds_polyline():
    svc = MockMapService()
    pts = [RoutePoint(lat=13.75, lng=100.50, title="A", event_id="1"), RoutePoint(lat=13.76, lng=100.51, title="B", event_id="2")]
    route = await svc.directions(pts)
    assert route is not None and len(route.encoded_polyline) > 0


async def test_mock_enrich_items_populates_place_id():
    svc = MockMapService()
    enriched = await svc.enrich_items([{"title": "Wat Pho"}])
    assert all(it["place_id"] for it in enriched)


async def test_backwards_compat_alias():
    assert MockGoogleMapsService is MockMapService


# ── V1 ────────────────────────────────────────────────────────────────────────

async def test_v1_find_place_ok():
    svc = MapServiceV1(api_key="k")
    payload = {"status": "OK", "candidates": [{"name": "C", "place_id": "c1", "geometry": {"location": {"lat": 41, "lng": 12}}}]}
    mc = _patched_client(_fake_response(payload))
    with patch("app.services.google_maps.v1.httpx.AsyncClient", return_value=mc):
        r = await svc.find_place("C")
    assert r["place_id"] == "c1"


async def test_v1_find_place_zero_results():
    svc = MapServiceV1(api_key="k")
    mc = _patched_client(_fake_response({"status": "ZERO_RESULTS", "candidates": []}))
    with patch("app.services.google_maps.v1.httpx.AsyncClient", return_value=mc):
        assert await svc.find_place("nope") is None


async def test_v1_cache_after_first_call():
    svc = MapServiceV1(api_key="k")
    payload = {"status": "OK", "candidates": [{"name": "E", "place_id": "e1", "geometry": {"location": {"lat": 48, "lng": 2}}}]}
    mc = _patched_client(_fake_response(payload))
    with patch("app.services.google_maps.v1.httpx.AsyncClient", return_value=mc):
        await svc.find_place("Eiffel")
        await svc.find_place("Eiffel")
    assert mc.request.await_count == 1


# ── V2 ────────────────────────────────────────────────────────────────────────

async def test_v2_find_place_ok():
    svc = MapServiceV2(api_key="k")
    payload = {"places": [{"id": "c1", "displayName": {"text": "C"}, "location": {"latitude": 1, "longitude": 2}}]}
    mc = _patched_client(_fake_response(payload))
    with patch("app.services.google_maps.v2.httpx.AsyncClient", return_value=mc):
        r = await svc.find_place("C")
    assert r["id"] == "c1"


async def test_v2_find_place_zero_results():
    svc = MapServiceV2(api_key="k")
    mc = _patched_client(_fake_response({}))
    with patch("app.services.google_maps.v2.httpx.AsyncClient", return_value=mc):
        assert await svc.find_place("nope") is None


# ── Factory ───────────────────────────────────────────────────────────────────

async def test_factory_returns_mock_when_GOOGLE_MAPS_MOCK_true(monkeypatch):
    from app.services import google_maps as pkg
    pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", True)
    assert isinstance(get_google_maps_service(), MockMapService)
    pkg.get_google_maps_service.cache_clear()


async def test_factory_returns_v1_by_default(monkeypatch):
    from app.services import google_maps as pkg
    pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", False)
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "real")
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_VERSION", "v1")
    assert isinstance(get_google_maps_service(), MapServiceV1)
    pkg.get_google_maps_service.cache_clear()


async def test_factory_returns_v2_when_configured(monkeypatch):
    from app.services import google_maps as pkg
    pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", False)
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "real")
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_VERSION", "v2")
    assert isinstance(get_google_maps_service(), MapServiceV2)
    pkg.get_google_maps_service.cache_clear()


async def test_factory_falls_back_to_mock_when_key_missing(monkeypatch):
    from app.services import google_maps as pkg
    pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", False)
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "")
    assert isinstance(get_google_maps_service(), MockMapService)
    pkg.get_google_maps_service.cache_clear()


# ── Feature flags ─────────────────────────────────────────────────────────────

async def test_v1_apply_details_skips_rating_when_flag_off(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    svc = MapServiceV1(api_key="k")
    item: dict = {"title": "X"}
    svc._apply_details(item, {"place_id": "p", "geometry": {"location": {"lat": 10, "lng": 20}}, "formatted_address": "A", "rating": 4.5, "price_level": 2, "photos": [{"photo_reference": "r"}], "types": ["bar"]})
    assert "rating" not in item and "price_level" not in item


async def test_v1_apply_details_skips_photos_when_flag_off(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_PHOTOS", False)
    svc = MapServiceV1(api_key="k")
    item: dict = {"title": "X"}
    svc._apply_details(item, {"place_id": "p", "geometry": {"location": {"lat": 10, "lng": 20}}, "formatted_address": "A", "rating": 4.5, "price_level": 2, "photos": [{"photo_reference": "r"}], "types": ["bar"]})
    assert "photo_url" not in item


async def test_v2_apply_details_skips_rating_when_flag_off(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    svc = MapServiceV2(api_key="k")
    item: dict = {"title": "X"}
    svc._apply_details(item, {"id": "p", "location": {"latitude": 10, "longitude": 20}, "formattedAddress": "A", "rating": 4.5, "priceLevel": "PRICE_LEVEL_EXPENSIVE", "photos": [{"name": "p/photos/a"}], "types": ["bar"]})
    assert "rating" not in item and "price_level" not in item


async def test_v2_apply_details_skips_photos_when_flag_off(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_PHOTOS", False)
    svc = MapServiceV2(api_key="k")
    item: dict = {"title": "X"}
    svc._apply_details(item, {"id": "p", "location": {"latitude": 10, "longitude": 20}, "formattedAddress": "A", "rating": 4.5, "priceLevel": "PRICE_LEVEL_EXPENSIVE", "photos": [{"name": "p/photos/a"}], "types": ["bar"]})
    assert "photo_url" not in item


async def test_mock_apply_details_skips_rating_when_flag_off(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_RATING", False)
    svc = MockMapService()
    enriched = await svc.enrich_items([{"title": "Wat Pho"}])
    assert "rating" not in enriched[0]


async def test_mock_apply_details_skips_photos_when_flag_off(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_FETCH_PHOTOS", False)
    svc = MockMapService()
    enriched = await svc.enrich_items([{"title": "Wat Pho"}])
    assert "photo_url" not in enriched[0]
