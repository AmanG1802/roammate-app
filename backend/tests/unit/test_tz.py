"""Unit tests for app.utils.tz — timezone helper functions.

All functions are pure datetime transforms with no DB or network.
"""
import pytest
from datetime import datetime, date, time, timezone, timedelta
from zoneinfo import ZoneInfo

from app.utils.tz import (
    utc_now,
    to_utc,
    from_utc,
    today_in_tz,
    combine_in_tz,
    split_in_tz,
    ensure_utc,
)


class TestUtcNow:
    def test_utc_now(self):
        # Test 1a - Returns timezone-aware datetime in UTC
        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

        # Test 1b - Result is close to actual current time
        before = datetime.now(timezone.utc)
        result = utc_now()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestToUtc:
    def test_to_utc(self):
        # Test 1a - Convert naive datetime in IST to UTC (IST = UTC+5:30)
        naive_ist = datetime(2025, 6, 15, 12, 0, 0)
        result = to_utc(naive_ist, "Asia/Kolkata")
        assert result.tzinfo == timezone.utc
        assert result == datetime(2025, 6, 15, 6, 30, 0, tzinfo=timezone.utc)

        # Test 1b - Convert naive datetime in US/Eastern (EDT = UTC-4) to UTC
        naive_edt = datetime(2025, 7, 1, 10, 0, 0)
        result = to_utc(naive_edt, "America/New_York")
        assert result.tzinfo == timezone.utc
        assert result.hour == 14

        # Test 1c - Already tz-aware datetime is converted directly
        aware = datetime(2025, 6, 15, 12, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        result = to_utc(aware, "Ignored/Timezone")
        assert result.tzinfo == timezone.utc
        assert result == datetime(2025, 6, 15, 3, 0, 0, tzinfo=timezone.utc)

        # Test 1d - UTC timezone passthrough
        naive_utc = datetime(2025, 1, 1, 0, 0, 0)
        result = to_utc(naive_utc, "UTC")
        assert result == datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


class TestFromUtc:
    def test_from_utc(self):
        # Test 1a - Convert UTC to IST
        utc_dt = datetime(2025, 6, 15, 6, 30, 0, tzinfo=timezone.utc)
        result = from_utc(utc_dt, "Asia/Kolkata")
        assert result.hour == 12
        assert result.minute == 0

        # Test 1b - Convert UTC to Tokyo (JST = UTC+9)
        utc_dt = datetime(2025, 6, 15, 3, 0, 0, tzinfo=timezone.utc)
        result = from_utc(utc_dt, "Asia/Tokyo")
        assert result.hour == 12
        assert result.minute == 0

        # Test 1c - Naive UTC is treated as UTC before conversion
        naive = datetime(2025, 1, 1, 12, 0, 0)
        result = from_utc(naive, "Asia/Kolkata")
        assert result.hour == 17
        assert result.minute == 30


class TestTodayInTz:
    def test_today_in_tz(self):
        # Test 1a - Returns a date object
        result = today_in_tz("Asia/Kolkata")
        assert isinstance(result, date)

        # Test 1b - Correct date for timezone ahead of UTC near midnight
        # If UTC is 23:30 on Jan 1, IST is 05:00 on Jan 2
        # We can't control utc_now easily in a pure test but verify type
        result = today_in_tz("UTC")
        assert isinstance(result, date)


class TestCombineInTz:
    def test_combine_in_tz(self):
        # Test 1a - Normal combination in IST returns UTC
        d = date(2025, 6, 15)
        t = time(12, 0, 0)
        result = combine_in_tz(d, t, "Asia/Kolkata")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result == datetime(2025, 6, 15, 6, 30, 0, tzinfo=timezone.utc)

        # Test 1b - None day returns None
        assert combine_in_tz(None, t, "UTC") is None

        # Test 1c - None time returns None
        assert combine_in_tz(d, None, "UTC") is None

        # Test 1d - Both None returns None
        assert combine_in_tz(None, None, "UTC") is None

        # Test 1e - Invalid timezone name falls back to UTC
        result = combine_in_tz(d, t, "Invalid/Zone")
        assert result is not None
        assert result == datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Test 1f - None tz_name falls back to UTC
        result = combine_in_tz(d, t, None)
        assert result is not None
        assert result == datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestSplitInTz:
    def test_split_in_tz(self):
        # Test 1a - Split UTC instant into IST components
        utc_dt = datetime(2025, 6, 15, 6, 30, 0, tzinfo=timezone.utc)
        day, t = split_in_tz(utc_dt, "Asia/Kolkata")
        assert day == date(2025, 6, 15)
        assert t == time(12, 0, 0)

        # Test 1b - Naive datetime is treated as UTC
        naive = datetime(2025, 6, 15, 6, 30, 0)
        day, t = split_in_tz(naive, "Asia/Kolkata")
        assert day == date(2025, 6, 15)
        assert t == time(12, 0, 0)

        # Test 1c - Invalid tz_name falls back to UTC
        utc_dt = datetime(2025, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
        day, t = split_in_tz(utc_dt, "Bad/Zone")
        assert day == date(2025, 1, 1)
        assert t == time(15, 0, 0)

        # Test 1d - None tz_name falls back to UTC
        day, t = split_in_tz(utc_dt, None)
        assert day == date(2025, 1, 1)
        assert t == time(15, 0, 0)

        # Test 1e - Time returned has no tzinfo (stripped)
        day, t = split_in_tz(utc_dt, "Asia/Tokyo")
        assert t.tzinfo is None


class TestEnsureUtc:
    def test_ensure_utc(self):
        # Test 1a - None returns None
        assert ensure_utc(None) is None

        # Test 1b - Naive datetime gets UTC tzinfo
        naive = datetime(2025, 1, 1, 12, 0, 0)
        result = ensure_utc(naive)
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 12

        # Test 1c - Already UTC datetime is passthrough
        utc_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(utc_dt)
        assert result == utc_dt

        # Test 1d - Non-UTC aware datetime is converted to UTC
        tokyo = datetime(2025, 1, 1, 21, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        result = ensure_utc(tokyo)
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result == datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestCombineSplitRoundtrip:
    @pytest.mark.parametrize("tz_name", [
        "Asia/Kolkata", "America/New_York", "Europe/London",
        "Asia/Tokyo", "Australia/Sydney", "UTC",
    ])
    def test_roundtrip(self, tz_name: str):
        # Test 1a - combine then split returns original values
        d = date(2025, 3, 15)
        t = time(14, 30, 0)
        utc_instant = combine_in_tz(d, t, tz_name)
        assert utc_instant is not None
        result_day, result_time = split_in_tz(utc_instant, tz_name)
        assert result_day == d
        assert result_time == t
