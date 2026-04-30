"""Unit tests for the versioned GoogleMapsService package (V1, V2, Mock)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.google_maps import (
    MockMapService,
    MockGoogleMapsService,
    RoutePoint,
    get_google_maps_service,
)
from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.breaker import breaker
from app.services.google_maps.v1 import MapServiceV1
from app.services.google_maps.v2 import MapServiceV2


@pytest.fixture(autouse=True)
async def _reset_state():
    """Each test gets a clean cache + a fresh circuit breaker."""
    gmap_cache.clear_all()
    breaker._state.failure_times.clear()
    breaker._state.opened_at = None
    breaker._state.half_open = False
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def _fake_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json.return_value = payload
    return resp


def _patched_client(resp: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.request = AsyncMock(return_value=resp)
    return mock_client


# ── MockMapService ───────────────────────────────────────────────────────────


async def test_mock_find_place_returns_full_shape():
    svc = MockMapService()
    result = await svc.find_place("Colosseum")
    assert result is not None
    assert result["displayName"]["text"] == "Colosseum"
    assert result["id"].startswith("mock_id_")
    assert "location" in result
    assert "latitude" in result["location"] and "longitude" in result["location"]


async def test_mock_place_details_drops_legacy_fields():
    svc = MockMapService()
    details = await svc.place_details("mock_id_test")
    assert details is not None
    assert "formatted_phone_number" not in details
    assert "website" not in details
    assert "opening_hours" not in details
    assert details["rating"] is not None
    assert details["priceLevel"] == "PRICE_LEVEL_MODERATE"


async def test_mock_directions_builds_polyline():
    svc = MockMapService()
    waypoints = [
        RoutePoint(lat=13.75, lng=100.50, title="A", event_id="1"),
        RoutePoint(lat=13.76, lng=100.51, title="B", event_id="2"),
    ]
    route = await svc.directions(waypoints)
    assert route is not None
    assert len(route.encoded_polyline) > 0
    assert len(route.legs) == 1
    assert route.total_duration_s > 0


async def test_mock_enrich_items_populates_place_id():
    svc = MockMapService()
    items = [{"title": "Wat Pho"}, {"title": "Chatuchak"}]
    enriched = await svc.enrich_items(items)
    assert all(it["place_id"] for it in enriched)
    assert all(it["lat"] is not None and it["lng"] is not None for it in enriched)


async def test_backwards_compat_alias():
    """``MockGoogleMapsService`` is an alias for ``MockMapService``."""
    assert MockGoogleMapsService is MockMapService


# ── MapServiceV1 (legacy, mocked HTTP) ───────────────────────────────────────


async def test_v1_find_place_ok():
    svc = MapServiceV1(api_key="test-key")
    payload = {
        "status": "OK",
        "candidates": [
            {
                "name": "Colosseum",
                "place_id": "c1",
                "geometry": {"location": {"lat": 41.89, "lng": 12.49}},
                "formatted_address": "Rome",
            }
        ],
    }
    mock_client = _patched_client(_fake_response(payload))
    with patch(
        "app.services.google_maps.v1.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await svc.find_place("Colosseum")
    assert result is not None
    assert result["place_id"] == "c1"
    assert result["name"] == "Colosseum"


async def test_v1_find_place_zero_results():
    svc = MapServiceV1(api_key="test-key")
    payload = {"status": "ZERO_RESULTS", "candidates": []}
    mock_client = _patched_client(_fake_response(payload))
    with patch(
        "app.services.google_maps.v1.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await svc.find_place("nowhere-zzz")
    assert result is None


async def test_v1_place_details_ok():
    svc = MapServiceV1(api_key="test-key")
    payload = {
        "status": "OK",
        "result": {
            "place_id": "p1",
            "name": "Grand Palace",
            "geometry": {"location": {"lat": 13.75, "lng": 100.49}},
            "formatted_address": "Bangkok",
            "rating": 4.6,
            "price_level": 2,
            "photos": [{"photo_reference": "ref_abc"}],
            "types": ["tourist_attraction"],
        },
    }
    mock_client = _patched_client(_fake_response(payload))
    with patch(
        "app.services.google_maps.v1.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await svc.place_details("p1")
    assert result is not None
    assert result["place_id"] == "p1"
    assert result["rating"] == 4.6


async def test_v1_apply_details_maps_fields():
    svc = MapServiceV1(api_key="test-key")
    item: dict = {"title": "Foo"}
    details = {
        "place_id": "p2",
        "geometry": {"location": {"lat": 10.0, "lng": 20.0}},
        "formatted_address": "Addr",
        "rating": 3.9,
        "price_level": 3,
        "photos": [{"photo_reference": "ref_xyz"}],
        "types": ["bar"],
    }
    svc._apply_details(item, details)
    assert item["place_id"] == "p2"
    assert item["lat"] == 10.0
    assert item["lng"] == 20.0
    assert item["address"] == "Addr"
    assert item["rating"] == 3.9
    assert item["price_level"] == 3
    assert "photo_url" in item
    assert "ref_xyz" in item["photo_url"]
    # Dropped fields must not be populated.
    assert "phone" not in item
    assert "website" not in item
    assert "opening_hours" not in item


async def test_v1_extract_place_id():
    svc = MapServiceV1(api_key="test-key")
    candidate = {"place_id": "abc", "name": "X"}
    assert svc._extract_place_id(candidate) == "abc"


async def test_v1_cache_after_first_call():
    svc = MapServiceV1(api_key="test-key")
    payload = {
        "status": "OK",
        "candidates": [
            {
                "name": "Eiffel",
                "place_id": "e1",
                "geometry": {"location": {"lat": 48.85, "lng": 2.29}},
            }
        ],
    }
    mock_client = _patched_client(_fake_response(payload))
    with patch(
        "app.services.google_maps.v1.httpx.AsyncClient",
        return_value=mock_client,
    ):
        first = await svc.find_place("Eiffel Tower")
        second = await svc.find_place("Eiffel Tower")
    assert first == second
    assert mock_client.request.await_count == 1


# ── MapServiceV2 (new API, mocked HTTP) ─────────────────────────────────────


async def test_v2_find_place_ok():
    svc = MapServiceV2(api_key="test-key")
    payload = {
        "places": [
            {
                "id": "c1",
                "displayName": {"text": "Colosseum", "languageCode": "en"},
                "location": {"latitude": 1, "longitude": 2},
                "formattedAddress": "Rome",
            }
        ]
    }
    mock_client = _patched_client(_fake_response(payload))
    with patch(
        "app.services.google_maps.v2.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await svc.find_place("Colosseum")
    assert result is not None
    assert result["id"] == "c1"
    assert result["displayName"]["text"] == "Colosseum"


async def test_v2_find_place_zero_results():
    svc = MapServiceV2(api_key="test-key")
    mock_client = _patched_client(_fake_response({}))
    with patch(
        "app.services.google_maps.v2.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await svc.find_place("nowhere-zzz")
    assert result is None


async def test_v2_place_details_drops_unwanted_fields():
    svc = MapServiceV2(api_key="test-key")
    payload = {
        "id": "p1",
        "displayName": {"text": "Spot", "languageCode": "en"},
        "formattedAddress": "Mock",
        "location": {"latitude": 13.7, "longitude": 100.5},
        "rating": 4.2,
        "priceLevel": "PRICE_LEVEL_INEXPENSIVE",
        "photos": [{"name": "places/p1/photos/abc"}],
        "types": ["restaurant"],
    }
    mock_client = _patched_client(_fake_response(payload))
    with patch(
        "app.services.google_maps.v2.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await svc.place_details("p1")
    assert result is not None

    call = mock_client.request.await_args
    field_mask = call.kwargs["headers"]["X-Goog-FieldMask"]
    assert "openingHours" not in field_mask
    assert "internationalPhoneNumber" not in field_mask
    assert "websiteUri" not in field_mask
    assert "rating" in field_mask
    assert "priceLevel" in field_mask


async def test_v2_apply_details_maps_price_level_enum():
    svc = MapServiceV2(api_key="test-key")
    item: dict = {"title": "Foo"}
    details = {
        "id": "p2",
        "location": {"latitude": 10.0, "longitude": 20.0},
        "formattedAddress": "Addr",
        "rating": 3.9,
        "priceLevel": "PRICE_LEVEL_EXPENSIVE",
        "photos": [{"name": "places/p2/photos/abc"}],
        "types": ["bar"],
    }
    svc._apply_details(item, details)
    assert item["price_level"] == 3
    assert item["place_id"] == "p2"
    assert item["lat"] == 10.0
    assert item["lng"] == 20.0
    assert item["address"] == "Addr"
    assert item["rating"] == 3.9
    assert "phone" not in item
    assert "website" not in item
    assert "opening_hours" not in item


async def test_v2_extract_place_id():
    svc = MapServiceV2(api_key="test-key")
    candidate = {"id": "abc", "displayName": {"text": "X"}}
    assert svc._extract_place_id(candidate) == "abc"


async def test_v2_cache_after_first_call():
    svc = MapServiceV2(api_key="test-key")
    payload = {
        "places": [
            {
                "id": "e1",
                "displayName": {"text": "Eiffel", "languageCode": "en"},
                "location": {"latitude": 48.85, "longitude": 2.29},
            }
        ]
    }
    mock_client = _patched_client(_fake_response(payload))
    with patch(
        "app.services.google_maps.v2.httpx.AsyncClient",
        return_value=mock_client,
    ):
        first = await svc.find_place("Eiffel Tower")
        second = await svc.find_place("Eiffel Tower")
    assert first == second
    assert mock_client.request.await_count == 1


# ── Factory ──────────────────────────────────────────────────────────────────


async def test_factory_returns_mock_when_GOOGLE_MAPS_MOCK_true(monkeypatch):
    from app.services import google_maps as gmap_pkg

    gmap_pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", True)
    svc = get_google_maps_service()
    assert isinstance(svc, MockMapService)
    gmap_pkg.get_google_maps_service.cache_clear()


async def test_factory_returns_v1_by_default(monkeypatch):
    from app.services import google_maps as gmap_pkg

    gmap_pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", False)
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "real")
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_VERSION", "v1")
    svc = get_google_maps_service()
    assert isinstance(svc, MapServiceV1)
    gmap_pkg.get_google_maps_service.cache_clear()


async def test_factory_returns_v2_when_configured(monkeypatch):
    from app.services import google_maps as gmap_pkg

    gmap_pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", False)
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "real")
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_VERSION", "v2")
    svc = get_google_maps_service()
    assert isinstance(svc, MapServiceV2)
    gmap_pkg.get_google_maps_service.cache_clear()


async def test_factory_falls_back_to_mock_when_key_missing(monkeypatch):
    from app.services import google_maps as gmap_pkg

    gmap_pkg.get_google_maps_service.cache_clear()
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_MOCK", False)
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "")
    svc = get_google_maps_service()
    assert isinstance(svc, MockMapService)
    gmap_pkg.get_google_maps_service.cache_clear()
