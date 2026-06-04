"""Unit tests for app.services.google_maps.geocoding — pure helper functions.

Tests _country_only and _extract_latlng (no network). The async geocode_city
function is partially integration-tier due to cache access.
"""
import pytest
from app.services.google_maps.geocoding import _country_only, _extract_latlng


class TestCountryOnly:
    def test_country_only(self):
        # Test 1a - Valid country_code returns LocationContext with only country
        result = _country_only("IN")
        assert result is not None
        assert result.country_code == "IN"
        assert result.lat is None
        assert result.lng is None

        # Test 1b - None country_code returns None
        assert _country_only(None) is None

        # Test 1c - Empty string returns None
        assert _country_only("") is None


class TestExtractLatlng:
    def test_extract_v2_format(self):
        # Test 1a - v2/Apple format: location.latitude / location.longitude
        candidate = {"location": {"latitude": 13.75, "longitude": 100.50}}
        lat, lng = _extract_latlng(candidate)
        assert lat == 13.75
        assert lng == 100.50

    def test_extract_v1_location_format(self):
        # Test 1b - v1 direct: location.lat / location.lng
        candidate = {"location": {"lat": 48.8566, "lng": 2.3522}}
        lat, lng = _extract_latlng(candidate)
        assert lat == 48.8566
        assert lng == 2.3522

    def test_extract_v1_geometry_format(self):
        # Test 1c - v1 geometry: geometry.location.lat/lng
        candidate = {"geometry": {"location": {"lat": 35.68, "lng": 139.76}}}
        lat, lng = _extract_latlng(candidate)
        assert lat == 35.68
        assert lng == 139.76

    def test_extract_apple_center_format(self):
        # Test 1d - Apple Maps: center.lat / center.lng
        candidate = {"center": {"lat": -33.87, "lng": 151.21}}
        lat, lng = _extract_latlng(candidate)
        assert lat == -33.87
        assert lng == 151.21

    def test_extract_none_candidate(self):
        # Test 1e - None candidate returns (None, None)
        lat, lng = _extract_latlng(None)
        assert lat is None
        assert lng is None

    def test_extract_empty_dict(self):
        # Test 1f - Empty dict returns (None, None)
        lat, lng = _extract_latlng({})
        assert lat is None
        assert lng is None

    def test_extract_missing_fields(self):
        # Test 1g - Location present but missing lat/lng
        candidate = {"location": {"name": "test"}}
        lat, lng = _extract_latlng(candidate)
        assert lat is None
        assert lng is None

    def test_extract_string_coords_cast_to_float(self):
        # Test 1h - String coordinates are cast to float
        candidate = {"location": {"latitude": "13.75", "longitude": "100.50"}}
        lat, lng = _extract_latlng(candidate)
        assert lat == 13.75
        assert lng == 100.50
