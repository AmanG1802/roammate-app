"""Unit tests for RippleEngine.

Events store (day_date, start_time, end_time) as (DATE, TIME, TIME) in
trip-local wall-clock. ``shift_itinerary`` still accepts a UTC instant as
``start_from_time``; the engine combines event (day, time) → UTC instant
in the trip's tz, compares to that, and shifts wall-clock TIMEs by the
requested delta. UTC is the default trip tz, so the math is straightforward
in these tests.
"""
from datetime import date, datetime, time, timedelta, timezone
import pytest

from app.services.ripple_engine import ripple_engine
from app.models.all_models import TimelineItem as Event, Trip, User

DAY = date(2026, 6, 1)


@pytest.fixture
async def _seeded(db_session):
    user = User(email="u@x.com", name="U", hashed_password="h")
    db_session.add(user)
    await db_session.flush()
    trip = Trip(name="T", created_by_id=user.id, timezone="UTC")
    db_session.add(trip)
    await db_session.commit()
    return trip


async def _add_event(db, trip_id, start: time | None, end: time | None = None,
                     is_locked=False, title="E", day=DAY):
    evt = Event(
        trip_id=trip_id, title=title, day_date=day,
        start_time=start, end_time=end,
        is_locked=is_locked,
    )
    db.add(evt)
    await db.flush()
    return evt


def _utc(h, m=0):
    return datetime(DAY.year, DAY.month, DAY.day, h, m, tzinfo=timezone.utc)


async def test_shifts_future_events(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0))
    await db_session.commit()

    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=_utc(9, 0),
    )
    assert len(shifted) == 1
    assert shifted[0].start_time == time(10, 30)
    assert shifted[0].end_time == time(11, 30)


async def test_skips_past_events(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(8, 0), time(9, 0))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=_utc(9, 0),
    )
    assert shifted == []


async def test_skips_locked(db_session, _seeded):
    await _add_event(
        db_session, _seeded.id, time(10, 0), time(11, 0), is_locked=True,
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=_utc(9, 0),
    )
    assert shifted == []


async def test_skips_events_with_none_start(db_session, _seeded):
    await _add_event(db_session, _seeded.id, None, None, title="untimed")
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0), title="timed")
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=_utc(9, 0),
    )
    assert len(shifted) == 1
    assert shifted[0].title == "timed"


async def test_handles_none_end_time(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), None)
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=15,
        start_from_time=_utc(9, 0),
    )
    assert shifted[0].start_time == time(10, 15)
    assert shifted[0].end_time is None


async def test_negative_delta(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=-60,
        start_from_time=_utc(9, 0),
    )
    assert shifted[0].start_time == time(9, 0)


async def test_zero_delta_is_noop(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=0,
        start_from_time=_utc(9, 0),
    )
    assert shifted[0].start_time == time(10, 0)


async def test_returns_ordered_by_start_time(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(14, 0), time(15, 0), title="later")
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0), title="earlier")
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=5,
        start_from_time=_utc(9, 0),
    )
    assert [e.title for e in shifted] == ["earlier", "later"]


async def test_cross_midnight_shift_is_skipped(db_session, _seeded):
    """A shift that would push the event past midnight in trip-local terms
    is silently dropped by the legacy engine (smart_ripple raises instead)."""
    await _add_event(db_session, _seeded.id, time(23, 30), time(23, 45))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=120,
        start_from_time=_utc(9, 0),
    )
    assert shifted == []
