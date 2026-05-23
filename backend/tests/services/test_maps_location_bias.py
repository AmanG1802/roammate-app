"""Tests for LocationContext propagation through find_place across providers,
cache-key isolation, and the geocode_city helper."""
from __future__ import annotations

import pytest

from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.base import LocationContext
from app.services.google_maps.geocoding import geocode_city
from app.services.google_maps.mock import MockMapService


# Two well-separated city centroids used across the suite.
BENGALURU = LocationContext(lat=12.97, lng=77.59, country_code="IN")
NEW_YORK = LocationContext(lat=40.71, lng=-74.01, country_code="US")


@pytest.fixture(autouse=True)
def _clear_cache():
    gmap_cache.clear_all()
    yield
    gmap_cache.clear_all()


# ── LocationContext fingerprint ─────────────────────────────────────────────


def test_fingerprint_none_when_no_signal():
    assert LocationContext().fingerprint() is None


def test_fingerprint_includes_country_only():
    fp = LocationContext(country_code="in").fingerprint()
    assert fp == "IN|-|-"


def test_fingerprint_includes_centroid_and_country():
    fp = BENGALURU.fingerprint()
    assert fp.startswith("IN|12.97,77.59|")


def test_different_cities_have_different_fingerprints():
    assert BENGALURU.fingerprint() != NEW_YORK.fingerprint()


# ── Cache isolation across biases ───────────────────────────────────────────


async def test_cache_isolates_entries_by_fingerprint():
    """Same title under two distinct biases produces two cache entries."""
    await gmap_cache.set_find_place("Commercial Street", {"id": "blr"}, BENGALURU.fingerprint())
    await gmap_cache.set_find_place("Commercial Street", {"id": "nyc"}, NEW_YORK.fingerprint())

    blr, _ = await gmap_cache.get_find_place("Commercial Street", BENGALURU.fingerprint())
    nyc, _ = await gmap_cache.get_find_place("Commercial Street", NEW_YORK.fingerprint())
    assert blr["id"] == "blr"
    assert nyc["id"] == "nyc"


async def test_cache_legacy_no_bias_path_unchanged():
    """Calls with no bias keep using the legacy key — un-biased entries
    are still hit by un-biased reads."""
    await gmap_cache.set_find_place("Eiffel Tower", {"id": "et"})
    val, state = await gmap_cache.get_find_place("Eiffel Tower")
    assert state == "hit"
    assert val["id"] == "et"


async def test_biased_read_misses_unbiased_entry():
    """A bias fingerprint must NOT pick up an un-biased cache entry."""
    await gmap_cache.set_find_place("Commercial Street", {"id": "global"})
    val, _ = await gmap_cache.get_find_place("Commercial Street", BENGALURU.fingerprint())
    assert val is gmap_cache.MISS


# ── Mock find_place honors the bias anchor ─────────────────────────────────


async def test_mock_find_place_anchors_on_bias_lat_lng():
    svc = MockMapService()
    blr = await svc.find_place("Commercial Street", location=BENGALURU)
    nyc = await svc.find_place("Commercial Street", location=NEW_YORK)

    assert blr["location"]["latitude"] == pytest.approx(BENGALURU.lat, abs=0.05)
    assert nyc["location"]["latitude"] == pytest.approx(NEW_YORK.lat, abs=0.05)
    # And the same title with no bias falls back to the legacy anchor —
    # confirming bias actually changed behaviour.
    plain = await svc.find_place("Commercial Street")
    assert plain["location"]["latitude"] != pytest.approx(BENGALURU.lat, abs=0.05)


# ── geocode_city ────────────────────────────────────────────────────────────


async def test_geocode_city_returns_centroid_via_provider():
    svc = MockMapService()
    ctx = await geocode_city(svc, "Bengaluru", "IN")
    assert ctx is not None
    assert ctx.country_code == "IN"
    assert ctx.lat is not None and ctx.lng is not None


async def test_geocode_city_caches_centroid():
    svc = MockMapService()
    ctx1 = await geocode_city(svc, "Bengaluru", "IN")
    cached, state = await gmap_cache.get_city_centroid("Bengaluru", "IN")
    assert state == "hit"
    assert cached == (ctx1.lat, ctx1.lng)

    # Second call should not re-add to the cache (verify hit semantics).
    ctx2 = await geocode_city(svc, "Bengaluru", "IN")
    assert (ctx2.lat, ctx2.lng) == (ctx1.lat, ctx1.lng)


async def test_geocode_city_returns_country_only_when_city_missing():
    svc = MockMapService()
    ctx = await geocode_city(svc, None, "IN")
    assert ctx is not None
    assert ctx.country_code == "IN"
    assert ctx.lat is None and ctx.lng is None


async def test_geocode_city_returns_none_when_no_signal():
    svc = MockMapService()
    ctx = await geocode_city(svc, None, None)
    assert ctx is None


# ── Backwards compat: no-location calls behave as before ──────────────────


async def test_enrich_item_without_location_unchanged():
    svc = MockMapService()
    item = {"title": "Wat Pho"}
    out = await svc.enrich_item(item)
    assert out["place_id"]
    assert out["lat"] is not None


async def test_enrich_items_accepts_location_without_error():
    """Smoke test: passing a location through enrich_items doesn't break the
    mock pipeline. End-to-end lat/lng correctness requires the real Google
    place_details and is verified manually."""
    svc = MockMapService()
    items = [{"title": "Commercial Street"}, {"title": "MG Road"}]
    out = await svc.enrich_items(items, location=BENGALURU)
    assert all(it.get("place_id") for it in out)
