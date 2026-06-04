"""§25 Maps Location Bias & Geocoding — cache isolation by fingerprint and geocode_city."""
from __future__ import annotations

import pytest

from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.base import LocationContext
from app.services.google_maps.geocoding import geocode_city
from app.services.google_maps.mock import MockMapService

BENGALURU = LocationContext(lat=12.97, lng=77.59, country_code="IN")
NEW_YORK = LocationContext(lat=40.71, lng=-74.01, country_code="US")


@pytest.fixture(autouse=True)
def _clear():
    gmap_cache.clear_all()
    yield
    gmap_cache.clear_all()


async def test_cache_isolates_entries_by_fingerprint():
    await gmap_cache.set_find_place("Commercial Street", {"id": "blr"}, BENGALURU.fingerprint())
    await gmap_cache.set_find_place("Commercial Street", {"id": "nyc"}, NEW_YORK.fingerprint())
    blr, _ = await gmap_cache.get_find_place("Commercial Street", BENGALURU.fingerprint())
    nyc, _ = await gmap_cache.get_find_place("Commercial Street", NEW_YORK.fingerprint())
    assert blr["id"] == "blr" and nyc["id"] == "nyc"


async def test_biased_read_misses_unbiased_entry():
    await gmap_cache.set_find_place("Commercial Street", {"id": "global"})
    val, _ = await gmap_cache.get_find_place("Commercial Street", BENGALURU.fingerprint())
    assert val is gmap_cache.MISS


async def test_mock_find_place_anchors_on_bias_lat_lng():
    svc = MockMapService()
    blr = await svc.find_place("Commercial Street", location=BENGALURU)
    nyc = await svc.find_place("Commercial Street", location=NEW_YORK)
    assert blr["location"]["latitude"] == pytest.approx(BENGALURU.lat, abs=0.05)
    assert nyc["location"]["latitude"] == pytest.approx(NEW_YORK.lat, abs=0.05)


async def test_geocode_city_returns_centroid_via_provider():
    svc = MockMapService()
    ctx = await geocode_city(svc, "Bengaluru", "IN")
    assert ctx is not None and ctx.lat is not None


async def test_geocode_city_caches_centroid():
    svc = MockMapService()
    ctx1 = await geocode_city(svc, "Bengaluru", "IN")
    cached, state = await gmap_cache.get_city_centroid("Bengaluru", "IN")
    assert state == "hit" and cached == (ctx1.lat, ctx1.lng)


async def test_geocode_city_returns_country_only_when_city_missing():
    svc = MockMapService()
    ctx = await geocode_city(svc, None, "IN")
    assert ctx is not None and ctx.country_code == "IN" and ctx.lat is None


async def test_geocode_city_returns_none_when_no_signal():
    svc = MockMapService()
    assert await geocode_city(svc, None, None) is None


async def test_enrich_items_accepts_location_without_error():
    svc = MockMapService()
    out = await svc.enrich_items([{"title": "MG Road"}], location=BENGALURU)
    assert all(it.get("place_id") for it in out)
