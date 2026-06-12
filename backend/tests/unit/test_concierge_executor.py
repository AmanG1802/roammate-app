"""Unit tests for app.services.concierge_executor.

Covers:
  - _category_from_types (pure)
  - _event_dict (pure serialisation)
  - _parse_time_param (pure time parsing)
  - ConciergeExecutor.execute dispatcher + every intent handler
    (async, using the shared SQLite test DB via db_session fixture)
"""
import pytest
from datetime import date, time, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.concierge_executor import (
    _category_from_types,
    _event_dict,
    _parse_time_param,
    _TYPE_TO_CATEGORY,
    ConciergeExecutor,
)


# ── Pure helpers ─────────────────────────────────────────────────────────────


class TestCategoryFromTypes:
    def test_known_types(self):
        assert _category_from_types(["restaurant"]) == "Food & Dining"
        assert _category_from_types(["museum"]) == "Culture & Arts"
        assert _category_from_types(["park"]) == "Outdoors & Nature"
        assert _category_from_types(["bar"]) == "Nightlife"
        assert _category_from_types(["shopping_mall"]) == "Shopping"
        assert _category_from_types(["tourist_attraction"]) == "Sightseeing"
        assert _category_from_types(["atm"]) == "Utilities"

    def test_first_matching_type_wins(self):
        assert _category_from_types(["park", "restaurant"]) == "Outdoors & Nature"

    def test_unknown_types_fallback(self):
        assert _category_from_types(["xyz_unknown"]) == "Activity"

    def test_empty_list_fallback(self):
        assert _category_from_types([]) == "Activity"

    def test_mixed_unknown_then_known(self):
        assert _category_from_types(["unknown", "cafe"]) == "Food & Dining"

    def test_all_mapped_types_produce_category(self):
        for type_key, category in _TYPE_TO_CATEGORY.items():
            assert isinstance(category, str) and len(category) > 0
            assert _category_from_types([type_key]) == category


class TestEventDict:
    def _mock_event(self, **overrides):
        defaults = dict(
            id=1, trip_id=10, title="Lunch", place_id="ChIJ_abc",
            location_name="The Spot", lat=13.75, lng=100.50,
            day_date=date(2025, 7, 1), start_time=time(12, 0),
            end_time=time(13, 0), is_locked=False, sort_order=1,
            category="Food & Dining", is_skipped=False, address="123 St",
            photo_url="https://img.test/1.jpg", rating=4.5,
            price_level=2, description="Tasty", types=["restaurant"],
            time_category="afternoon", added_by="Alice",
        )
        defaults.update(overrides)
        ev = MagicMock()
        for k, v in defaults.items():
            setattr(ev, k, v)
        return ev

    def test_full_serialization(self):
        ev = self._mock_event()
        d = _event_dict(ev)
        assert d["id"] == 1
        assert d["trip_id"] == 10
        assert d["title"] == "Lunch"
        assert d["day_date"] == "2025-07-01"
        assert d["start_time"] == "12:00:00"
        assert d["end_time"] == "13:00:00"
        assert d["lat"] == 13.75
        assert d["category"] == "Food & Dining"

    def test_none_day_date_and_times(self):
        ev = self._mock_event(day_date=None, start_time=None, end_time=None)
        d = _event_dict(ev)
        assert d["day_date"] is None
        assert d["start_time"] is None
        assert d["end_time"] is None


class TestParseTimeParam:
    def test_bare_hh_mm(self):
        t = _parse_time_param("14:30", "UTC")
        assert t == time(14, 30, 0)

    def test_bare_hh_mm_ss(self):
        t = _parse_time_param("09:15:45", "UTC")
        assert t == time(9, 15, 0)  # seconds from split ignored; only h/m used in bare

    def test_bare_hour_only(self):
        t = _parse_time_param("8", "UTC")
        assert t == time(8, 0, 0)

    def test_iso_datetime_utc(self):
        t = _parse_time_param("2025-07-01T14:30:00Z", "UTC")
        assert t == time(14, 30)

    def test_iso_datetime_with_tz_converts_to_trip_tz(self):
        t = _parse_time_param("2025-07-01T12:00:00+00:00", "Asia/Kolkata")
        assert t == time(17, 30)  # UTC 12:00 → IST 17:30

    def test_iso_datetime_offset_converted(self):
        t = _parse_time_param("2025-07-01T10:00:00+05:30", "UTC")
        assert t == time(4, 30)  # IST 10:00 → UTC 04:30


# ── Async executor tests (use db_session from conftest) ──────────────────────


@pytest.fixture
def executor():
    return ConciergeExecutor()


async def _seed_user(db, name="Alice"):
    from app.models.all_models import User as UserModel
    user = UserModel(name=name, email=f"{name.lower()}@test.com", hashed_password="x")
    db.add(user)
    await db.flush()
    return user


async def _seed_trip(db, user):
    from app.models.all_models import Trip, TripMember
    trip = Trip(name="T", created_by_id=user.id)
    db.add(trip)
    await db.flush()
    db.add(TripMember(trip_id=trip.id, user_id=user.id, role="admin", status="accepted"))
    await db.commit()
    return trip


async def _seed_event(db, trip_id, **kw):
    from app.models.all_models import TimelineItem as EventModel
    defaults = dict(
        trip_id=trip_id, title="Museum Visit",
        day_date=date(2025, 7, 1), start_time=time(10, 0),
        end_time=time(11, 0), is_locked=False, is_skipped=False,
    )
    defaults.update(kw)
    ev = EventModel(**defaults)
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


class TestExecuteDispatch:
    async def test_unknown_intent(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "unknown_action", {}, db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False
        assert "Unknown intent" in result["message"]

    async def test_dispatch_uses_user_name_as_added_by(self, db_session, executor):
        user = await _seed_user(db_session, name="Bob")
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "add_event",
            {"title": "Coffee Break"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert result["new_event"]["added_by"] == "Bob"

    async def test_dispatch_fallback_added_by_when_no_name(self, db_session, executor):
        from app.models.all_models import User as UserModel, Trip, TripMember
        user = UserModel(name=None, email="noname@test.com", hashed_password="x")
        db_session.add(user)
        await db_session.flush()
        trip = Trip(name="T", created_by_id=user.id)
        db_session.add(trip)
        await db_session.flush()
        db_session.add(TripMember(trip_id=trip.id, user_id=user.id, role="admin", status="accepted"))
        await db_session.commit()

        result = await executor.execute(
            "add_event",
            {"title": "Walk"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert result["new_event"]["added_by"] == f"user:{user.id}"


class TestSkipEvent:
    async def test_skip_success(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        ev = await _seed_event(db_session, trip_id=trip.id)
        result = await executor.execute(
            "skip_event", {"event_id": ev.id},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert "Skipped" in result["message"]
        assert result["updated_events"][0]["is_skipped"] is True

    async def test_skip_missing_event_id(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "skip_event", {},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False
        assert "Missing event_id" in result["message"]

    async def test_skip_event_not_found(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "skip_event", {"event_id": 9999},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False
        assert "not found" in result["message"]

    async def test_skip_event_wrong_trip(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        ev = await _seed_event(db_session, trip_id=trip.id)
        result = await executor.execute(
            "skip_event", {"event_id": ev.id},
            db_session, trip_id=999, user_id=user.id,
        )
        assert result["success"] is False


class TestMoveEvent:
    async def test_move_time(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        ev = await _seed_event(db_session, trip_id=trip.id,
                               start_time=time(10, 0), end_time=time(11, 0))
        result = await executor.execute(
            "move_event",
            {"event_id": ev.id, "new_start_time": "14:00"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        moved = result["updated_events"][0]
        assert moved["start_time"] == "14:00:00"
        assert moved["end_time"] == "15:00:00"  # duration preserved

    async def test_move_cross_day_rejected(self, db_session, executor):
        # A7: cross-day moves via chat are rejected (the cascade is same-day);
        # the user is told to drag on the timeline instead.
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        ev = await _seed_event(db_session, trip_id=trip.id)  # day_date 2025-07-01
        result = await executor.execute(
            "move_event",
            {"event_id": ev.id, "new_day_date": "2025-08-01"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False
        assert "drag" in result["message"].lower()
        await db_session.refresh(ev)
        assert ev.day_date == date(2025, 7, 1)

    async def test_move_same_day_with_explicit_day(self, db_session, executor):
        # Passing the event's own day alongside a new time is a same-day move.
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        ev = await _seed_event(db_session, trip_id=trip.id,
                               start_time=time(10, 0), end_time=time(11, 0))
        result = await executor.execute(
            "move_event",
            {"event_id": ev.id, "new_start_time": "16:00", "new_day_date": "2025-07-01"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        moved = next(e for e in result["updated_events"] if e["id"] == ev.id)
        assert moved["start_time"] == "16:00:00"
        assert moved["day_date"] == "2025-07-01"

    async def test_move_event_no_end_time(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        ev = await _seed_event(db_session, trip_id=trip.id,
                               start_time=time(10, 0), end_time=None)
        result = await executor.execute(
            "move_event",
            {"event_id": ev.id, "new_start_time": "15:00"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        moved = result["updated_events"][0]
        assert moved["start_time"] == "15:00:00"
        assert moved["end_time"] == "16:00:00"  # default +1h

    async def test_move_missing_event_id(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "move_event", {},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False

    async def test_move_event_not_found(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "move_event", {"event_id": 9999},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False


class TestAddEvent:
    async def test_add_minimal(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "add_event", {"title": "Dinner"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert result["new_event"]["title"] == "Dinner"
        assert result["new_event"]["day_date"] is not None  # defaults to today

    async def test_add_with_times(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "add_event",
            {"title": "Spa", "start_time": "14:00", "end_time": "16:00",
             "day_date": "2025-07-10"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        ev = result["new_event"]
        assert ev["start_time"] == "14:00:00"
        assert ev["end_time"] == "16:00:00"
        assert ev["day_date"] == "2025-07-10"

    async def test_add_auto_end_time(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "add_event",
            {"title": "Hike", "start_time": "09:00"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        ev = result["new_event"]
        assert ev["start_time"] == "09:00:00"
        assert ev["end_time"] == "10:00:00"  # +1h default

    async def test_add_with_place_details(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "add_event",
            {"title": "Cafe", "place_id": "ChIJ_xyz", "lat": 13.5,
             "lng": 100.2, "category": "Food & Dining",
             "address": "456 Ave", "rating": 4.2, "price_level": 1,
             "types": ["cafe"], "description": "Cozy place",
             "photo_url": "https://img/2.jpg"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        ev = result["new_event"]
        assert ev["place_id"] == "ChIJ_xyz"
        assert ev["lat"] == 13.5
        assert ev["category"] == "Food & Dining"

    async def test_add_missing_title(self, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "add_event", {},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False
        assert "Missing title" in result["message"]


class TestShiftTimeline:
    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_shift_calls_engine(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        ev = MagicMock()
        ev.title = "Lunch"
        mock_engine.shift_itinerary = AsyncMock(return_value=[ev])

        result = await executor.execute(
            "shift_timeline",
            {"delta_minutes": 30, "start_from_event_id": 5},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert "1 event(s)" in result["message"]
        mock_engine.shift_itinerary.assert_awaited_once()
        call_kw = mock_engine.shift_itinerary.call_args.kwargs
        assert call_kw["delta_minutes"] == 30
        assert call_kw["start_from_event_id"] == 5

    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_shift_no_events(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        mock_engine.shift_itinerary = AsyncMock(return_value=[])

        result = await executor.execute(
            "shift_timeline", {"delta_minutes": 15},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert "No events" in result["message"]

    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_shift_many_events_truncated_message(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        events = [MagicMock(title=f"Ev{i}") for i in range(5)]
        mock_engine.shift_itinerary = AsyncMock(return_value=events)

        result = await executor.execute(
            "shift_timeline", {"delta_minutes": 10},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert "5 event(s)" in result["message"]
        assert "2 more" in result["message"]

    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_shift_default_delta(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        mock_engine.shift_itinerary = AsyncMock(return_value=[])
        await executor.execute(
            "shift_timeline", {},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert mock_engine.shift_itinerary.call_args.kwargs["delta_minutes"] == 15


class TestAddNearby:
    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_add_nearby_success(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        mock_engine.shift_itinerary = AsyncMock(return_value=[])

        result = await executor.execute(
            "find_nearby",
            {"title": "Pharmacy", "place_id": "ChIJ_pharm",
             "lat": 13.7, "lng": 100.5, "types": ["pharmacy"],
             "address": "789 Rd"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert result["new_event"]["title"] == "Pharmacy"
        assert result["new_event"]["category"] == "Utilities"  # from types

    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_add_nearby_missing_title(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        result = await executor.execute(
            "find_nearby", {},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is False
        assert "Missing" in result["message"]

    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_add_nearby_with_explicit_start_time(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        mock_engine.shift_itinerary = AsyncMock(return_value=[])

        result = await executor.execute(
            "find_nearby",
            {"title": "ATM", "start_time": "15:00",
             "day_date": "2025-07-01"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert result["new_event"]["start_time"] == "15:00:00"

    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_add_nearby_with_explicit_category(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        mock_engine.shift_itinerary = AsyncMock(return_value=[])

        result = await executor.execute(
            "find_nearby",
            {"title": "Custom", "category": "Custom Cat", "types": ["xyz"]},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert result["new_event"]["category"] == "Custom Cat"

    @patch("app.services.concierge_executor.smart_ripple_engine")
    async def test_add_nearby_ripple_propagates_updates(self, mock_engine, db_session, executor):
        user = await _seed_user(db_session)
        trip = await _seed_trip(db_session, user)
        shifted_ev = await _seed_event(db_session, trip_id=trip.id, title="Next Stop")
        mock_engine.shift_itinerary = AsyncMock(return_value=[shifted_ev])

        result = await executor.execute(
            "find_nearby",
            {"title": "Quick Stop", "place_id": "ChIJ_qs"},
            db_session, trip_id=trip.id, user_id=user.id,
        )
        assert result["success"] is True
        assert len(result["updated_events"]) == 1
        assert result["updated_events"][0]["title"] == "Next Stop"
