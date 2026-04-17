"""Unit tests for RippleEngine."""
from datetime import datetime, timedelta
import pytest

from app.services.ripple_engine import ripple_engine
from app.models.all_models import Event, Trip, User


@pytest.fixture
async def _seeded(db_session):
    user = User(email="u@x.com", name="U", hashed_password="h")
    db_session.add(user)
    await db_session.flush()
    trip = Trip(name="T", created_by_id=user.id)
    db_session.add(trip)
    await db_session.commit()
    return trip


async def _add_event(db, trip_id, start, end=None, is_locked=False, title="E"):
    evt = Event(
        trip_id=trip_id, title=title,
        start_time=start, end_time=end,
        is_locked=is_locked,
    )
    db.add(evt)
    await db.flush()
    return evt


async def test_shifts_future_events(db_session, _seeded):
    start = datetime(2026, 6, 1, 10, 0)
    await _add_event(db_session, _seeded.id, start, start + timedelta(hours=1))
    await db_session.commit()

    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert len(shifted) == 1
    assert shifted[0].start_time == datetime(2026, 6, 1, 10, 30)
    assert shifted[0].end_time == datetime(2026, 6, 1, 11, 30)


async def test_skips_past_events(db_session, _seeded):
    await _add_event(
        db_session, _seeded.id,
        datetime(2026, 6, 1, 8, 0), datetime(2026, 6, 1, 9, 0),
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert shifted == []


async def test_skips_locked(db_session, _seeded):
    await _add_event(
        db_session, _seeded.id,
        datetime(2026, 6, 1, 10, 0), datetime(2026, 6, 1, 11, 0),
        is_locked=True,
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert shifted == []


async def test_skips_events_with_none_start(db_session, _seeded):
    """Previously crashed; after fix, these are filtered out."""
    await _add_event(db_session, _seeded.id, None, None, title="untimed")
    await _add_event(
        db_session, _seeded.id,
        datetime(2026, 6, 1, 10, 0), datetime(2026, 6, 1, 11, 0),
        title="timed",
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=30,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert len(shifted) == 1
    assert shifted[0].title == "timed"


async def test_handles_none_end_time(db_session, _seeded):
    """After fix, end_time=None is OK; start_time still shifts."""
    await _add_event(
        db_session, _seeded.id, datetime(2026, 6, 1, 10, 0), None,
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=15,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert shifted[0].start_time == datetime(2026, 6, 1, 10, 15)
    assert shifted[0].end_time is None


async def test_negative_delta(db_session, _seeded):
    await _add_event(
        db_session, _seeded.id,
        datetime(2026, 6, 1, 10, 0), datetime(2026, 6, 1, 11, 0),
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=-60,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert shifted[0].start_time == datetime(2026, 6, 1, 9, 0)


async def test_zero_delta_is_noop(db_session, _seeded):
    await _add_event(
        db_session, _seeded.id,
        datetime(2026, 6, 1, 10, 0), datetime(2026, 6, 1, 11, 0),
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=0,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert shifted[0].start_time == datetime(2026, 6, 1, 10, 0)


async def test_returns_ordered_by_start_time(db_session, _seeded):
    await _add_event(
        db_session, _seeded.id,
        datetime(2026, 6, 1, 14, 0), datetime(2026, 6, 1, 15, 0), title="later",
    )
    await _add_event(
        db_session, _seeded.id,
        datetime(2026, 6, 1, 10, 0), datetime(2026, 6, 1, 11, 0), title="earlier",
    )
    await db_session.commit()
    shifted = await ripple_engine.shift_itinerary(
        db=db_session, trip_id=_seeded.id, delta_minutes=5,
        start_from_time=datetime(2026, 6, 1, 9, 0),
    )
    assert [e.title for e in shifted] == ["earlier", "later"]
