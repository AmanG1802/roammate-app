"""Unit tests for app.services.tutorial_fixtures — static NYC tutorial data.

Validates structure integrity of the frozen tutorial dataset.
"""
import pytest
from app.services.tutorial_fixtures import (
    TRIP_NAME,
    TRIP_TIMEZONE,
    DESTINATION_CITY,
    COUNTRY_CODE,
    DESTINATION_LAT,
    DESTINATION_LNG,
)


class TestTutorialFixtureConstants:
    def test_tutorial_constants(self):
        # Test 1a - Trip name is non-empty
        assert isinstance(TRIP_NAME, str)
        assert len(TRIP_NAME) > 0

        # Test 1b - Timezone is a valid IANA timezone string
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(TRIP_TIMEZONE)
        assert tz is not None

        # Test 1c - Destination city and country code are set
        assert DESTINATION_CITY == "New York"
        assert COUNTRY_CODE == "US"

        # Test 1d - Coordinates are in valid range for NYC
        assert 40.0 < DESTINATION_LAT < 41.0
        assert -74.5 < DESTINATION_LNG < -73.0
