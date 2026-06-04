"""Unit tests for app.services.google_maps.cache — key building and normalization.

Tests the pure synchronous key-builder functions and normalization logic.
The async get/set functions touch Redis and in-memory caches so are partly
integration-tier, but the key construction logic is pure.
"""
import pytest
import hashlib
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.google_maps.cache import (
    _normalize_query,
    _find_place_key,
    _directions_key,
    _timezone_key,
    _city_centroid_key,
    _rk_find_place,
    _rk_place_details,
    _rk_directions,
    _rk_timezone,
    _from_redis,
    _CacheMiss,
    MISS,
    clear_all,
)


class TestNormalizeQuery:
    def test_normalize_query(self):
        # Test 1a - Strips leading/trailing whitespace and casefolds
        assert _normalize_query("  Hello World  ") == "hello world"

        # Test 1b - Already normalized string is unchanged
        assert _normalize_query("tokyo tower") == "tokyo tower"

        # Test 1c - Mixed case
        assert _normalize_query("Eiffel TOWER Paris") == "eiffel tower paris"

        # Test 1d - Empty string
        assert _normalize_query("") == ""


class TestFindPlaceKey:
    def test_find_place_key(self):
        # Test 1a - Key is (normalized_query, bias_fp)
        key = _find_place_key("Tokyo Tower", None)
        assert key == ("tokyo tower", None)

        # Test 1b - With bias_fp
        key = _find_place_key("Tokyo Tower", "35.65,139.74")
        assert key == ("tokyo tower", "35.65,139.74")

        # Test 1c - Whitespace in query is stripped
        key = _find_place_key("  Eiffel Tower  ", None)
        assert key == ("eiffel tower", None)


class TestDirectionsKey:
    def test_directions_key(self):
        # Test 1a - Returns a hashable tuple of (mode, waypoints_tuple)
        key = _directions_key(["ChIJ_a", "ChIJ_b"], "driving")
        assert key == ("driving", ("ChIJ_a", "ChIJ_b"))

        # Test 1b - Different mode produces different key
        key1 = _directions_key(["A", "B"], "driving")
        key2 = _directions_key(["A", "B"], "walking")
        assert key1 != key2

        # Test 1c - Order of waypoints matters
        key1 = _directions_key(["A", "B"], "driving")
        key2 = _directions_key(["B", "A"], "driving")
        assert key1 != key2


class TestTimezoneKey:
    def test_timezone_key(self):
        # Test 1a - Rounds to 2 decimal places (~1km grid)
        key = _timezone_key(13.7537, 100.5022)
        assert key == (13.75, 100.50)

        # Test 1b - Negative coordinates
        key = _timezone_key(-33.8688, 151.2093)
        assert key == (-33.87, 151.21)

        # Test 1c - Zero coordinates
        key = _timezone_key(0.0, 0.0)
        assert key == (0.0, 0.0)

        # Test 1d - Already rounded values unchanged
        key = _timezone_key(10.00, 20.00)
        assert key == (10.0, 20.0)


class TestCityCentroidKey:
    def test_city_centroid_key(self):
        # Test 1a - City is casefolded, country_code uppercased
        key = _city_centroid_key("Tokyo", "jp")
        assert key == ("tokyo", "JP")

        # Test 1b - Whitespace is stripped
        key = _city_centroid_key("  Bangkok  ", "  th  ")
        assert key == ("bangkok", "TH")

        # Test 1c - None country_code becomes empty string
        key = _city_centroid_key("Paris", None)
        assert key == ("paris", "")


class TestRedisKeyBuilders:
    def test_rk_find_place(self):
        # Test 1a - Returns a string starting with "gmap:find_place:"
        key = _rk_find_place("tokyo tower", None)
        assert key.startswith("gmap:find_place:")

        # Test 1b - Different queries produce different keys
        k1 = _rk_find_place("tokyo tower", None)
        k2 = _rk_find_place("eiffel tower", None)
        assert k1 != k2

        # Test 1c - Same query with different bias_fp produces different keys
        k1 = _rk_find_place("test", None)
        k2 = _rk_find_place("test", "35.0,139.0")
        assert k1 != k2

    def test_rk_place_details(self):
        # Test 1a - Contains place_id and fields_sig
        key = _rk_place_details("ChIJ_abc", "basic,photos")
        assert "ChIJ_abc" in key
        assert "basic,photos" in key
        assert key.startswith("gmap:place_details:")

    def test_rk_directions(self):
        # Test 1a - Returns hash-based key
        key = _rk_directions(["ChIJ_a", "ChIJ_b"], "driving")
        assert key.startswith("gmap:directions:driving:")

        # Test 1b - Different mode in key
        key = _rk_directions(["A", "B"], "walking")
        assert "walking" in key

    def test_rk_timezone(self):
        # Test 1a - Contains rounded coordinates
        key = _rk_timezone(13.75, 100.50)
        assert key.startswith("gmap:timezone:")
        assert "13.75" in key
        assert "100.5" in key


class TestFromRedis:
    def test_from_redis(self):
        # Test 1a - "down" state returns None (triggers TTLCache fallback)
        result = _from_redis(None, "down")
        assert result is None

        # Test 1b - "hit" state returns (value, "hit")
        result = _from_redis({"place_id": "abc"}, "hit")
        assert result == ({"place_id": "abc"}, "hit")

        # Test 1c - "negative_hit" returns (None, "negative_hit")
        result = _from_redis(None, "negative_hit")
        assert result == (None, "negative_hit")

        # Test 1d - "miss" returns (MISS, "miss")
        result = _from_redis(None, "miss")
        assert result[0] is MISS
        assert result[1] == "miss"


class TestMissSentinel:
    def test_miss_sentinel(self):
        # Test 1a - MISS is a singleton-like sentinel
        assert MISS is not None
        assert isinstance(MISS, _CacheMiss)

        # Test 1b - MISS is not equal to None
        assert MISS != None  # noqa: E711

        # Test 1c - Can be used for identity checks
        assert MISS is MISS


class TestClearAll:
    def test_clear_all(self):
        # Test 1a - clear_all doesn't raise (smoke test)
        clear_all()  # Should not throw
