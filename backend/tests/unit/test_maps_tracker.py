"""Unit tests for app.services.google_maps.tracker — structured log emission.

Tests the track_call function's log assembly and _hash_query helper.
"""
import pytest
import logging
from unittest.mock import patch

from app.services.google_maps.tracker import track_call, _hash_query


class TestHashQuery:
    def test_hash_query(self):
        # Test 1a - Returns a 10-char hex hash
        result = _hash_query("Tokyo Tower")
        assert isinstance(result, str)
        assert len(result) == 10

        # Test 1b - None query returns None
        assert _hash_query(None) is None

        # Test 1c - Empty string returns None
        assert _hash_query("") is None

        # Test 1d - Same query (case-insensitive) produces same hash
        h1 = _hash_query("Eiffel Tower")
        h2 = _hash_query("eiffel tower")
        assert h1 == h2

        # Test 1e - Whitespace-normalized
        h1 = _hash_query("Tokyo Tower")
        h2 = _hash_query("  Tokyo Tower  ")
        assert h1 == h2

        # Test 1f - Different queries produce different hashes
        h1 = _hash_query("Place A")
        h2 = _hash_query("Place B")
        assert h1 != h2


class TestTrackCall:
    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_basic(self, mock_fire, caplog):
        # Test 1a - Basic track emits structured log with required fields
        with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
            track_call(op="place_details_v1", status="ok")

        assert "google_api" in caplog.text
        assert "op=place_details_v1" in caplog.text
        assert "status=ok" in caplog.text
        assert "latency_ms=0" in caplog.text
        assert "attempts=1" in caplog.text

    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_with_cache_state(self, mock_fire, caplog):
        # Test 1b - cache_state field included when provided
        with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
            track_call(op="find_place", status="cache_hit", cache_state="hit")

        assert "cache_state=hit" in caplog.text

    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_with_query_hashed(self, mock_fire, caplog):
        # Test 1c - Query is hashed (not raw) in the log
        with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
            track_call(op="find_place", status="ok", query="Secret Restaurant Name")

        assert "query_hash=" in caplog.text
        assert "Secret Restaurant Name" not in caplog.text

    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_with_all_optional_fields(self, mock_fire, caplog):
        # Test 1d - All optional fields logged when present
        with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
            track_call(
                op="directions",
                status="ok",
                latency_ms=250,
                attempts=2,
                cache_state="miss",
                breaker_state="closed",
                place_id="ChIJ_test",
                http_status=200,
                waypoint_count=3,
                total_distance_m=5000,
                total_duration_s=600,
                batch_size=5,
                enriched_count=4,
                skipped_count=1,
                user_id=42,
                trip_id=7,
            )

        log_text = caplog.text
        assert "latency_ms=250" in log_text
        assert "attempts=2" in log_text
        assert "breaker_state=closed" in log_text
        assert "place_id=ChIJ_test" in log_text
        assert "http_status=200" in log_text
        assert "waypoint_count=3" in log_text
        assert "total_distance_m=5000" in log_text
        assert "total_duration_s=600" in log_text
        assert "batch_size=5" in log_text
        assert "enriched_count=4" in log_text
        assert "skipped_count=1" in log_text
        assert "user_id=42" in log_text
        assert "trip_id=7" in log_text

    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_omits_none_fields(self, mock_fire, caplog):
        # Test 1e - None optional fields are NOT in the log
        with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
            track_call(op="test", status="ok")

        assert "place_id=" not in caplog.text
        assert "http_status=" not in caplog.text
        assert "waypoint_count=" not in caplog.text
        assert "user_id=" not in caplog.text

    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_fires_persist(self, mock_fire):
        # Test 1f - fire_and_forget is called to schedule DB write
        track_call(op="test", status="ok")
        mock_fire.assert_called_once()

    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_with_extra(self, mock_fire, caplog):
        # Test 1g - extra dict merges into log fields
        with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
            track_call(op="test", status="ok", extra={"custom_field": "value123"})

        assert "custom_field=value123" in caplog.text

    @patch("app.services.google_maps.tracker.fire_and_forget")
    def test_track_call_error_fields(self, mock_fire, caplog):
        # Test 1h - Error tracking fields
        with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
            track_call(
                op="place_details_v2",
                status="error",
                http_status=500,
                error_class="TimeoutError",
            )

        assert "status=error" in caplog.text
        assert "http_status=500" in caplog.text
        assert "error_class=TimeoutError" in caplog.text
