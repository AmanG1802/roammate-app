"""Unit tests for Pydantic schemas."""
from datetime import date, datetime, time, timezone, timedelta
import pytest
from pydantic import ValidationError

from app.schemas.event import EventCreate, EventUpdate, RippleRequest
from app.schemas.trip import TripCreate, TripUpdate, InviteRequest, IngestRequest
from app.utils.tz import ensure_utc


# ── ensure_utc helper ────────────────────────────────────────────────────────

def test_ensure_utc_none():
    assert ensure_utc(None) is None


def test_ensure_utc_naive_becomes_utc():
    dt = datetime(2026, 6, 1, 14, 0)
    out = ensure_utc(dt)
    assert out.tzinfo is not None
    assert out.tzinfo == timezone.utc
    assert out == datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)


def test_ensure_utc_already_utc_passthrough():
    dt = datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc)
    out = ensure_utc(dt)
    assert out == dt


def test_ensure_utc_non_utc_converts():
    tz = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2026, 6, 1, 14, 0, tzinfo=tz)
    out = ensure_utc(dt)
    assert out.tzinfo == timezone.utc
    assert out == datetime(2026, 6, 1, 8, 30, tzinfo=timezone.utc)


# ── Event schema TIME-only contract ─────────────────────────────────────────

def test_event_create_accepts_naive_time():
    e = EventCreate(
        trip_id=1, title="T",
        day_date=date(2026, 6, 1),
        start_time=time(14, 0),
        end_time=time(15, 0),
    )
    assert e.start_time == time(14, 0)
    assert e.end_time == time(15, 0)
    assert e.day_date == date(2026, 6, 1)


def test_event_create_parses_string_time():
    e = EventCreate(trip_id=1, title="T", start_time="14:30:00")
    assert e.start_time == time(14, 30, 0)


def test_event_create_rejects_overnight():
    with pytest.raises(ValidationError):
        EventCreate(
            trip_id=1, title="T",
            start_time=time(22, 0),
            end_time=time(2, 0),
        )


def test_event_update_accepts_time():
    e = EventUpdate(start_time=time(14, 0))
    assert e.start_time == time(14, 0)


def test_event_serializer_pins_hms():
    e = EventCreate(trip_id=1, title="T", start_time=time(14, 0, 0, 123_000))
    # microseconds are dropped on serialize
    assert e.model_dump()["start_time"] == "14:00:00"


def test_ripple_request_ensures_utc():
    r = RippleRequest(
        delta_minutes=10,
        start_from_time=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
    )
    assert r.start_from_time.tzinfo == timezone.utc


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


def test_trip_create_default_timezone():
    t = TripCreate(name="T")
    assert t.timezone == "UTC"


def test_trip_create_with_timezone():
    t = TripCreate(name="T", timezone="Asia/Bangkok")
    assert t.timezone == "Asia/Bangkok"


# ── Request schemas ───────────────────────────────────────────────────────────

def test_invite_request_default_role():
    r = InviteRequest(email="x@y.com")
    assert r.role == "view_only"


def test_ingest_request_requires_text():
    with pytest.raises(ValidationError):
        IngestRequest()


# ── Event / IdeaBinItem vote field defaults ───────────────────────────────────

from app.schemas.event import Event
from app.schemas.trip import IdeaBinItem


def test_event_schema_vote_defaults():
    e = Event(id=1, trip_id=1, title="T")
    assert e.up == 0 and e.down == 0 and e.my_vote == 0


def test_idea_bin_item_schema_vote_defaults():
    i = IdeaBinItem(id=1, trip_id=1, title="T")
    assert i.up == 0 and i.down == 0 and i.my_vote == 0
