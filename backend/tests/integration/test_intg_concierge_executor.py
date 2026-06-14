"""§9 Concierge Executor — DB-backed intent dispatch tests for skip, move, add,
shift timeline, and find-nearby.
"""
from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.services.concierge_executor import ConciergeExecutor
from app.models.all_models import User, Trip, TripMember, TimelineItem as Event


@pytest.fixture
def executor():
    return ConciergeExecutor()


async def _seed_user(db, name="Alice"):
    user = User(name=name, email=f"{name.lower()}@test.com", hashed_password="x")
    db.add(user)
    await db.flush()
    return user


async def _seed_trip(db, user):
    trip = Trip(name="Test Trip", created_by_id=user.id)
    db.add(trip)
    await db.flush()
    db.add(TripMember(trip_id=trip.id, user_id=user.id, role="admin", status="accepted"))
    await db.commit()
    return trip


async def _seed_event(db, trip_id, **kw):
    defaults = dict(
        trip_id=trip_id, title="Museum",
        day_date=date(2025, 7, 1), start_time=time(10, 0),
        end_time=time(11, 0), is_locked=False, is_skipped=False,
    )
    defaults.update(kw)
    ev = Event(**defaults)
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


async def test_executor_skip_event(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = await _seed_event(db_session, trip_id=trip.id)
    result = await executor.execute("skip_event", {"event_id": ev.id}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is True
    assert result["updated_events"][0]["is_skipped"] is True


async def test_executor_skip_event_missing_id(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("skip_event", {}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is False
    assert "Missing event_id" in result["message"]


async def test_executor_skip_event_not_found(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("skip_event", {"event_id": 9999}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is False


@patch("app.services.concierge_executor.smart_ripple_engine")
async def test_executor_shift_timeline(mock_engine, db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = MagicMock()
    ev.title = "Lunch"
    mock_engine.shift_itinerary = AsyncMock(return_value=[ev])
    result = await executor.execute("shift_timeline", {"delta_minutes": 30}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is True


@patch("app.services.concierge_executor.smart_ripple_engine")
async def test_executor_shift_timeline_no_events(mock_engine, db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    mock_engine.shift_itinerary = AsyncMock(return_value=[])
    result = await executor.execute("shift_timeline", {"delta_minutes": 15}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is True
    assert "No events" in result["message"]


async def test_executor_move_event_new_time(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = await _seed_event(db_session, trip_id=trip.id, start_time=time(10, 0), end_time=time(11, 0))
    result = await executor.execute("move_event", {"event_id": ev.id, "new_start_time": "14:00"}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is True
    assert result["updated_events"][0]["start_time"] == "14:00:00"


async def test_executor_move_event_cross_day_rejected(db_session, executor):
    # A7: cross-day moves via chat are rejected — drag on the timeline instead.
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = await _seed_event(db_session, trip_id=trip.id)  # day_date 2025-07-01
    result = await executor.execute("move_event", {"event_id": ev.id, "new_day_date": "2025-08-01"}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is False
    assert "drag" in result["message"].lower()


async def test_executor_move_event_not_found(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("move_event", {"event_id": 9999}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is False


async def test_executor_add_event(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("add_event", {"title": "Dinner"}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is True
    assert result["new_event"]["title"] == "Dinner"


async def test_executor_add_event_missing_title(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("add_event", {}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is False
    assert "Missing title" in result["message"]


async def test_executor_add_event_auto_end_time(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("add_event", {"title": "Hike", "start_time": "09:00"}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is True
    assert result["new_event"]["end_time"] == "10:00:00"


@patch("app.services.concierge_executor.smart_ripple_engine")
async def test_executor_find_nearby_adds_event_and_ripples(mock_engine, db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    mock_engine.shift_itinerary = AsyncMock(return_value=[])
    result = await executor.execute(
        "find_nearby",
        {"title": "Pharmacy", "place_id": "ChIJ_p", "lat": 13.7, "lng": 100.5, "types": ["pharmacy"]},
        db_session, trip_id=trip.id, user_id=user.id,
    )
    assert result["success"] is True
    assert result["new_event"]["title"] == "Pharmacy"


@patch("app.services.concierge_executor.smart_ripple_engine")
async def test_executor_find_nearby_missing_title(mock_engine, db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("find_nearby", {}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is False


async def test_executor_unknown_intent(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("unknown_action", {}, db_session, trip_id=trip.id, user_id=user.id)
    assert result["success"] is False
    assert "Unknown intent" in result["message"]


# ── 3.8 Undo ─────────────────────────────────────────────────────────────────

async def test_undo_move_restores_prior_time(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = await _seed_event(db_session, trip_id=trip.id, start_time=time(10, 0), end_time=time(11, 0))
    await executor.execute("move_event", {"event_id": ev.id, "new_start_time": "14:00"}, db_session, trip_id=trip.id, user_id=user.id)
    await db_session.refresh(ev)
    assert ev.start_time == time(14, 0)

    undo = await executor.undo(db_session, trip_id=trip.id, user_id=user.id)
    assert undo["success"] is True
    await db_session.refresh(ev)
    assert ev.start_time == time(10, 0)
    assert ev.end_time == time(11, 0)


async def test_undo_add_deletes_event(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    result = await executor.execute("add_event", {"title": "Dinner", "start_time": "19:00"}, db_session, trip_id=trip.id, user_id=user.id)
    new_id = result["new_event"]["id"]

    undo = await executor.undo(db_session, trip_id=trip.id, user_id=user.id)
    assert undo["success"] is True
    gone = (await db_session.execute(
        select(Event).where(Event.id == new_id)
    )).scalars().first()
    assert gone is None


async def test_undo_nothing_to_undo(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    undo = await executor.undo(db_session, trip_id=trip.id, user_id=user.id)
    assert undo["success"] is False
    assert "nothing" in undo["message"].lower()


async def test_undo_second_undo_is_noop(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = await _seed_event(db_session, trip_id=trip.id, start_time=time(10, 0), end_time=time(11, 0))
    await executor.execute("move_event", {"event_id": ev.id, "new_start_time": "14:00"}, db_session, trip_id=trip.id, user_id=user.id)
    first = await executor.undo(db_session, trip_id=trip.id, user_id=user.id)
    assert first["success"] is True
    second = await executor.undo(db_session, trip_id=trip.id, user_id=user.id)
    assert second["success"] is False


# ── 3.5/3.6 Dry-run preview ──────────────────────────────────────────────────

async def test_preview_move_event_persists_nothing(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = await _seed_event(db_session, trip_id=trip.id, start_time=time(10, 0), end_time=time(11, 0))

    preview = await executor.preview(
        "move_event", {"event_id": ev.id, "new_start_time": "14:00"},
        db_session, trip_id=trip.id, user_id=user.id,
    )
    assert preview is not None
    # The moved event shows up in the projected changes with new time…
    assert any(c.new_start == "14:00" for c in preview.changes)
    # …but nothing is committed: the row keeps its original time.
    await db_session.refresh(ev)
    assert ev.start_time == time(10, 0)


async def test_preview_cross_day_move_warns(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    ev = await _seed_event(db_session, trip_id=trip.id)
    preview = await executor.preview(
        "move_event", {"event_id": ev.id, "new_day_date": "2025-08-01"},
        db_session, trip_id=trip.id, user_id=user.id,
    )
    assert preview is not None
    assert any(w.kind == "cross_day" for w in preview.warnings)


async def test_preview_non_write_intent_returns_none(db_session, executor):
    user = await _seed_user(db_session)
    trip = await _seed_trip(db_session, user)
    preview = await executor.preview("explain_plan", {}, db_session, trip_id=trip.id, user_id=user.id)
    assert preview is None
