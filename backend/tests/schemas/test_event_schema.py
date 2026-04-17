"""Unit tests for Pydantic schemas."""
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError

from app.schemas.event import EventCreate, EventUpdate, RippleRequest, _strip_tz
from app.schemas.trip import TripCreate, TripUpdate, InviteRequest, IngestRequest


# ── Event tz stripping ────────────────────────────────────────────────────────

def test_strip_tz_none():
    assert _strip_tz(None) is None


def test_strip_tz_utc():
    dt = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
    out = _strip_tz(dt)
    assert out.tzinfo is None
    assert out == datetime(2026, 6, 1, 14, 0)


def test_strip_tz_non_utc():
    tz = timezone(timedelta(hours=5))
    dt = datetime(2026, 6, 1, 14, 0, tzinfo=tz)
    out = _strip_tz(dt)
    assert out.tzinfo is None
    assert out == datetime(2026, 6, 1, 9, 0)


def test_event_create_strips_tz_on_both_times():
    e = EventCreate(
        trip_id=1, title="T",
        start_time=datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc),
    )
    assert e.start_time.tzinfo is None
    assert e.end_time.tzinfo is None


def test_event_update_strips_tz():
    e = EventUpdate(start_time=datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc))
    assert e.start_time.tzinfo is None


def test_ripple_request_strips_tz():
    r = RippleRequest(
        delta_minutes=10,
        start_from_time=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
    )
    assert r.start_from_time.tzinfo is None


# ── Trip validators ───────────────────────────────────────────────────────────

def test_trip_create_rejects_end_before_start():
    with pytest.raises(ValidationError):
        TripCreate(
            name="T",
            start_date=datetime(2026, 6, 10),
            end_date=datetime(2026, 6, 5),
        )


def test_trip_create_accepts_equal_dates():
    TripCreate(
        name="T",
        start_date=datetime(2026, 6, 1),
        end_date=datetime(2026, 6, 1),
    )


def test_trip_update_rejects_end_before_start():
    with pytest.raises(ValidationError):
        TripUpdate(
            start_date=datetime(2026, 6, 10),
            end_date=datetime(2026, 6, 5),
        )


def test_trip_create_only_name_ok():
    TripCreate(name="T")


# ── Request schemas ───────────────────────────────────────────────────────────

def test_invite_request_default_role():
    r = InviteRequest(email="x@y.com")
    assert r.role == "view_only"


def test_ingest_request_requires_text():
    with pytest.raises(ValidationError):
        IngestRequest()
