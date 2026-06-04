"""§15 Ripple Engine — legacy ripple and smart ripple DB-backed tests."""
from __future__ import annotations

from datetime import date, datetime, time, timezone

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


async def _add_event(db, trip_id, start, end=None, is_locked=False, title="E", day=DAY):
    evt = Event(trip_id=trip_id, title=title, day_date=day, start_time=start, end_time=end, is_locked=is_locked)
    db.add(evt)
    await db.flush()
    return evt


def _utc(h, m=0):
    return datetime(DAY.year, DAY.month, DAY.day, h, m, tzinfo=timezone.utc)


async def test_legacy_ripple_shifts_events_by_delta(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=30, start_from_time=_utc(9))
    assert len(shifted) == 1
    assert shifted[0].start_time == time(10, 30)


async def test_legacy_ripple_skips_locked_events(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0), is_locked=True)
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=30, start_from_time=_utc(9))
    assert shifted == []


async def test_legacy_ripple_skips_past_events(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(8, 0), time(9, 0))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=30, start_from_time=_utc(9))
    assert shifted == []


async def test_legacy_ripple_skips_events_with_none_start(db_session, _seeded):
    await _add_event(db_session, _seeded.id, None, None, title="untimed")
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0), title="timed")
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=30, start_from_time=_utc(9))
    assert len(shifted) == 1 and shifted[0].title == "timed"


async def test_legacy_ripple_handles_none_end_time(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), None)
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=15, start_from_time=_utc(9))
    assert shifted[0].start_time == time(10, 15) and shifted[0].end_time is None


async def test_legacy_ripple_negative_delta_shifts_backward(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=-60, start_from_time=_utc(9))
    assert shifted[0].start_time == time(9, 0)


async def test_legacy_ripple_zero_delta_is_noop(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=0, start_from_time=_utc(9))
    assert shifted[0].start_time == time(10, 0)


async def test_legacy_ripple_returns_ordered_by_start_time(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(14, 0), time(15, 0), title="later")
    await _add_event(db_session, _seeded.id, time(10, 0), time(11, 0), title="earlier")
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=5, start_from_time=_utc(9))
    assert [e.title for e in shifted] == ["earlier", "later"]


async def test_cross_midnight_shift_is_skipped(db_session, _seeded):
    await _add_event(db_session, _seeded.id, time(23, 30), time(23, 45))
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(db=db_session, trip_id=_seeded.id, delta_minutes=120, start_from_time=_utc(9))
    assert shifted == []
