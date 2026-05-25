"""Unit tests for app.services.llm.token_tracker — structured log emission.

Tests the `track` function's log-line assembly. The fire-and-forget DB persist
is mocked out (it's an integration concern).
"""
import pytest
import logging
from unittest.mock import patch, MagicMock

from app.services.llm.models.base import LLMResponse
from app.services.llm.token_tracker import track


class TestTrack:
    @patch("app.services.llm.token_tracker.fire_and_forget")
    def test_track_basic_log(self, mock_fire, caplog):
        # Test 1a - Basic track call emits a log line with correct fields
        response = LLMResponse(
            content="hello",
            input_tokens=100,
            output_tokens=50,
            model="gpt-4o-mini",
            provider="openai",
        )
        with caplog.at_level(logging.INFO, logger="roammate.tokens"):
            track(response, operation="chat")

        assert "token_usage" in caplog.text
        assert "op=chat" in caplog.text
        assert "provider=openai" in caplog.text
        assert "model=gpt-4o-mini" in caplog.text
        assert "tokens_in=100" in caplog.text
        assert "tokens_out=50" in caplog.text
        assert "tokens_total=150" in caplog.text

    @patch("app.services.llm.token_tracker.fire_and_forget")
    def test_track_with_user_and_trip(self, mock_fire, caplog):
        # Test 1b - user_id and trip_id are included when provided
        response = LLMResponse(
            content="x", input_tokens=10, output_tokens=5,
            model="gemini-2.0-flash", provider="gemini",
        )
        with caplog.at_level(logging.INFO, logger="roammate.tokens"):
            track(response, operation="extract", user_id=42, trip_id=7)

        assert "user_id=42" in caplog.text
        assert "trip_id=7" in caplog.text

    @patch("app.services.llm.token_tracker.fire_and_forget")
    def test_track_with_source(self, mock_fire, caplog):
        # Test 1c - source field is logged
        response = LLMResponse(
            content="x", input_tokens=0, output_tokens=0,
            model="m", provider="p",
        )
        with caplog.at_level(logging.INFO, logger="roammate.tokens"):
            track(response, operation="plan_trip", source="brainstorm")

        assert "source=brainstorm" in caplog.text

    @patch("app.services.llm.token_tracker.fire_and_forget")
    def test_track_with_extra(self, mock_fire, caplog):
        # Test 1d - extra dict fields are merged into the log
        response = LLMResponse(
            content="x", input_tokens=0, output_tokens=0,
            model="m", provider="p",
        )
        with caplog.at_level(logging.INFO, logger="roammate.tokens"):
            track(response, operation="chat", extra={"attempt": 2})

        assert "attempt=2" in caplog.text

    @patch("app.services.llm.token_tracker.fire_and_forget")
    def test_track_fires_persist_coroutine(self, mock_fire):
        # Test 1e - fire_and_forget is called (async persist is scheduled)
        response = LLMResponse(
            content="x", input_tokens=10, output_tokens=20,
            model="m", provider="p",
        )
        track(response, operation="chat")
        mock_fire.assert_called_once()

    @patch("app.services.llm.token_tracker.fire_and_forget")
    def test_track_tokens_total_computed(self, mock_fire, caplog):
        # Test 1f - tokens_total = tokens_in + tokens_out
        response = LLMResponse(
            content="x", input_tokens=333, output_tokens=111,
            model="m", provider="p",
        )
        with caplog.at_level(logging.INFO, logger="roammate.tokens"):
            track(response, operation="test_op")

        assert "tokens_total=444" in caplog.text

    @patch("app.services.llm.token_tracker.fire_and_forget")
    def test_track_omits_none_fields(self, mock_fire, caplog):
        # Test 1g - user_id/trip_id/source omitted when None
        response = LLMResponse(
            content="x", input_tokens=0, output_tokens=0,
            model="m", provider="p",
        )
        with caplog.at_level(logging.INFO, logger="roammate.tokens"):
            track(response, operation="chat")

        assert "user_id" not in caplog.text
        assert "trip_id" not in caplog.text
        assert "source" not in caplog.text
