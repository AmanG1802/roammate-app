"""Unit tests for backend/app/utils/tz.py timezone utility module."""
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.utils.tz import utc_now, to_utc, from_utc, today_in_tz, ensure_utc


class TestUtcNow:
    def test_returns_aware_datetime(self):
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_close_to_real_utc(self):
        now = utc_now()
        expected = datetime.now(timezone.utc)
        assert abs((now - expected).total_seconds()) < 2


class TestToUtc:
    def test_naive_bangkok_to_utc(self):
        naive = datetime(2026, 5, 9, 14, 0)
        result = to_utc(naive, "Asia/Bangkok")
        assert result.tzinfo == timezone.utc
        assert result == datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc)

    def test_naive_utc_to_utc(self):
        naive = datetime(2026, 5, 9, 7, 0)
        result = to_utc(naive, "UTC")
        assert result == datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc)

    def test_aware_input_converts_directly(self):
        aware = datetime(2026, 5, 9, 14, 0, tzinfo=ZoneInfo("Asia/Bangkok"))
        result = to_utc(aware, "Asia/Bangkok")
        assert result.tzinfo == timezone.utc
        assert result == datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc)

    def test_kolkata_offset(self):
        naive = datetime(2026, 5, 9, 14, 0)
        result = to_utc(naive, "Asia/Kolkata")
        assert result == datetime(2026, 5, 9, 8, 30, tzinfo=timezone.utc)


class TestFromUtc:
    def test_utc_to_bangkok(self):
        utc_dt = datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc)
        result = from_utc(utc_dt, "Asia/Bangkok")
        assert result.hour == 14
        assert result.tzinfo is not None

    def test_utc_to_utc(self):
        utc_dt = datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc)
        result = from_utc(utc_dt, "UTC")
        assert result.hour == 7

    def test_naive_treated_as_utc(self):
        naive_utc = datetime(2026, 5, 9, 7, 0)
        result = from_utc(naive_utc, "Asia/Bangkok")
        assert result.hour == 14


class TestTodayInTz:
    def test_utc_returns_date(self):
        d = today_in_tz("UTC")
        assert isinstance(d, date)

    def test_different_tz_may_differ(self):
        utc_date = today_in_tz("UTC")
        assert isinstance(utc_date, date)


class TestEnsureUtc:
    def test_none_returns_none(self):
        assert ensure_utc(None) is None

    def test_naive_becomes_utc(self):
        naive = datetime(2026, 5, 9, 14, 0)
        result = ensure_utc(naive)
        assert result.tzinfo == timezone.utc
        assert result == datetime(2026, 5, 9, 14, 0, tzinfo=timezone.utc)

    def test_utc_passthrough(self):
        dt = datetime(2026, 5, 9, 14, 0, tzinfo=timezone.utc)
        result = ensure_utc(dt)
        assert result == dt

    def test_non_utc_converts(self):
        tz = timezone(timedelta(hours=5, minutes=30))
        dt = datetime(2026, 5, 9, 14, 0, tzinfo=tz)
        result = ensure_utc(dt)
        assert result.tzinfo == timezone.utc
        assert result == datetime(2026, 5, 9, 8, 30, tzinfo=timezone.utc)

    def test_bangkok_converts(self):
        dt = datetime(2026, 5, 9, 14, 0, tzinfo=ZoneInfo("Asia/Bangkok"))
        result = ensure_utc(dt)
        assert result.tzinfo == timezone.utc
        assert result == datetime(2026, 5, 9, 7, 0, tzinfo=timezone.utc)
