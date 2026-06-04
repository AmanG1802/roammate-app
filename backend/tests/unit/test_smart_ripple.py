"""Unit tests for app.services.smart_ripple — travel-time-aware ripple engine.

Tests static/pure methods (_apply_shift, _event_to_route_point,
CrossMidnightShiftError) AND the async shift_itinerary + _get_travel_minutes
methods using the shared SQLite test DB and mocked Maps service.
"""
import pytest
from datetime import date, time, timedelta, datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.smart_ripple import (
    SmartRippleEngine,
    CrossMidnightShiftError,
)
from app.services.google_maps import RoutePoint


def _make_event(
    id: int = 1,
    day_date: date = date(2025, 6, 15),
    start_time: time = time(10, 0),
    end_time: time | None = time(11, 0),
    place_id: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    title: str = "Test Event",
):
    event = MagicMock()
    event.id = id
    event.day_date = day_date
    event.start_time = start_time
    event.end_time = end_time
    event.place_id = place_id
    event.lat = lat
    event.lng = lng
    event.title = title
    return event


# ── _apply_shift ─────────────────────────────────────────────────────────────


class TestApplyShift:
    def test_shift_forward(self):
        event = _make_event(start_time=time(10, 0), end_time=time(11, 0))
        SmartRippleEngine._apply_shift(event, timedelta(minutes=30), "UTC")
        assert event.start_time == time(10, 30)
        assert event.end_time == time(11, 30)

    def test_shift_backward(self):
        event = _make_event(start_time=time(14, 0), end_time=time(15, 0))
        SmartRippleEngine._apply_shift(event, timedelta(minutes=-60), "UTC")
        assert event.start_time == time(13, 0)
        assert event.end_time == time(14, 0)

    def test_cross_midnight_raises(self):
        event = _make_event(start_time=time(23, 30), end_time=time(23, 50))
        with pytest.raises(CrossMidnightShiftError) as exc_info:
            SmartRippleEngine._apply_shift(event, timedelta(minutes=60), "UTC")
        assert exc_info.value.event_id == 1
        assert exc_info.value.original_day == date(2025, 6, 15)

    def test_no_end_time(self):
        event = _make_event(start_time=time(10, 0), end_time=None)
        SmartRippleEngine._apply_shift(event, timedelta(minutes=15), "UTC")
        assert event.start_time == time(10, 15)

    def test_zero_delta(self):
        event = _make_event(start_time=time(10, 0), end_time=time(11, 0))
        SmartRippleEngine._apply_shift(event, timedelta(minutes=0), "UTC")
        assert event.start_time == time(10, 0)
        assert event.end_time == time(11, 0)

    def test_with_timezone(self):
        event = _make_event(
            day_date=date(2025, 6, 15),
            start_time=time(22, 0), end_time=time(23, 0),
        )
        SmartRippleEngine._apply_shift(event, timedelta(minutes=30), "Asia/Kolkata")
        assert event.start_time == time(22, 30)
        assert event.end_time == time(23, 30)

    def test_end_time_cross_midnight_raises(self):
        event = _make_event(start_time=time(23, 0), end_time=time(23, 45))
        with pytest.raises(CrossMidnightShiftError):
            SmartRippleEngine._apply_shift(event, timedelta(minutes=30), "UTC")

    def test_none_day_date_is_noop(self):
        event = _make_event(day_date=None, start_time=time(10, 0))
        SmartRippleEngine._apply_shift(event, timedelta(minutes=30), "UTC")

    def test_end_time_combine_none_is_noop(self):
        event = _make_event(
            day_date=date(2025, 6, 15),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        SmartRippleEngine._apply_shift(event, timedelta(minutes=5), "UTC")
        assert event.start_time == time(10, 5)
        assert event.end_time == time(11, 5)


# ── _event_to_route_point ───────────────────────────────────────────────────


class TestEventToRoutePoint:
    def test_with_place_id(self):
        event = _make_event(place_id="ChIJ_test123", title="Test Place")
        result = SmartRippleEngine._event_to_route_point(event)
        assert result is not None
        assert result.place_id == "ChIJ_test123"
        assert result.title == "Test Place"

    def test_with_lat_lng(self):
        event = _make_event(place_id=None, lat=13.75, lng=100.50, title="Coord Place")
        result = SmartRippleEngine._event_to_route_point(event)
        assert result is not None
        assert result.lat == 13.75
        assert result.lng == 100.50

    def test_no_location(self):
        event = _make_event(place_id=None, lat=None, lng=None)
        result = SmartRippleEngine._event_to_route_point(event)
        assert result is None

    def test_place_id_takes_priority(self):
        event = _make_event(place_id="ChIJ_priority", lat=10.0, lng=20.0, title="Priority")
        result = SmartRippleEngine._event_to_route_point(event)
        assert result is not None
        assert result.place_id == "ChIJ_priority"


# ── CrossMidnightShiftError ─────────────────────────────────────────────────


class TestCrossMidnightShiftError:
    def test_error_attributes(self):
        err = CrossMidnightShiftError(42, date(2025, 6, 15), date(2025, 6, 16))
        assert err.event_id == 42
        assert err.original_day == date(2025, 6, 15)
        assert err.new_day == date(2025, 6, 16)

    def test_error_message(self):
        err = CrossMidnightShiftError(42, date(2025, 6, 15), date(2025, 6, 16))
        assert "42" in str(err)
        assert "not supported" in str(err).lower()

    def test_inherits_exception(self):
        err = CrossMidnightShiftError(1, date(2025, 1, 1), date(2025, 1, 2))
        assert isinstance(err, Exception)


# ── _get_travel_minutes ──────────────────────────────────────────────────────


class TestGetTravelMinutes:
    @pytest.fixture
    def engine(self):
        return SmartRippleEngine()

    async def test_returns_duration_from_directions(self, engine):
        prev = _make_event(place_id="A")
        curr = _make_event(place_id="B")

        leg = MagicMock()
        leg.duration_s = 900  # 15 minutes
        route = MagicMock()
        route.legs = [leg]
        maps_service = MagicMock()
        maps_service.directions = AsyncMock(return_value=route)

        result = await engine._get_travel_minutes(prev, curr, maps_service)
        assert result == 15.0

    async def test_returns_zero_when_no_route(self, engine):
        prev = _make_event(place_id="A")
        curr = _make_event(place_id="B")
        maps_service = MagicMock()
        maps_service.directions = AsyncMock(return_value=None)

        result = await engine._get_travel_minutes(prev, curr, maps_service)
        assert result == 0

    async def test_returns_zero_when_no_legs(self, engine):
        prev = _make_event(place_id="A")
        curr = _make_event(place_id="B")
        route = MagicMock()
        route.legs = []
        maps_service = MagicMock()
        maps_service.directions = AsyncMock(return_value=route)

        result = await engine._get_travel_minutes(prev, curr, maps_service)
        assert result == 0

    async def test_returns_zero_on_exception(self, engine):
        prev = _make_event(place_id="A")
        curr = _make_event(place_id="B")
        maps_service = MagicMock()
        maps_service.directions = AsyncMock(side_effect=Exception("API error"))

        result = await engine._get_travel_minutes(prev, curr, maps_service)
        assert result == 0

    async def test_returns_zero_when_no_location(self, engine):
        prev = _make_event(place_id=None, lat=None, lng=None)
        curr = _make_event(place_id="B")
        maps_service = MagicMock()
        maps_service.directions = AsyncMock()

        result = await engine._get_travel_minutes(prev, curr, maps_service)
        assert result == 0
        maps_service.directions.assert_not_awaited()

    async def test_passes_user_and_trip_ids(self, engine):
        prev = _make_event(place_id="A")
        curr = _make_event(place_id="B")
        maps_service = MagicMock()
        maps_service.directions = AsyncMock(return_value=None)

        await engine._get_travel_minutes(
            prev, curr, maps_service, user_id=7, trip_id=42,
        )
        maps_service.directions.assert_awaited_once()
        call_kw = maps_service.directions.call_args.kwargs
        assert call_kw["user_id"] == 7
        assert call_kw["trip_id"] == 42


# ── shift_itinerary (integration with test DB) ──────────────────────────────


async def _seed_trip(db, tz="UTC"):
    from app.models.all_models import Trip
    trip = Trip(name="Test Trip", timezone=tz)
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


async def _seed_event_db(db, trip_id, **kw):
    from app.models.all_models import TimelineItem as Event
    defaults = dict(
        trip_id=trip_id, title="Event",
        day_date=date(2025, 7, 1), start_time=time(10, 0),
        end_time=time(11, 0), is_locked=False, is_skipped=False,
    )
    defaults.update(kw)
    ev = Event(**defaults)
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


class TestShiftItinerary:
    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_no_events_returns_empty(self, mock_maps_factory, db_session):
        trip = await _seed_trip(db_session)
        engine = SmartRippleEngine()

        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=15,
        )
        assert result == []

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_single_event_shifted(self, mock_maps_factory, db_session):
        trip = await _seed_trip(db_session)
        ev = await _seed_event_db(
            db_session, trip.id,
            start_time=time(10, 0), end_time=time(11, 0),
            day_date=date(2025, 7, 1),
        )

        mock_maps = MagicMock()
        mock_maps.directions = AsyncMock(return_value=None)
        mock_maps_factory.return_value = mock_maps

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=30,
            start_from_event_id=ev.id,
        )
        assert len(result) == 1
        assert result[0].start_time == time(10, 30)
        assert result[0].end_time == time(11, 30)

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_locked_events_excluded(self, mock_maps_factory, db_session):
        trip = await _seed_trip(db_session)
        await _seed_event_db(db_session, trip.id, is_locked=True)

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=15,
        )
        assert result == []

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_skipped_events_excluded(self, mock_maps_factory, db_session):
        trip = await _seed_trip(db_session)
        await _seed_event_db(db_session, trip.id, is_skipped=True)

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=15,
        )
        assert result == []

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_event_id_not_found_returns_empty(self, mock_maps_factory, db_session):
        trip = await _seed_trip(db_session)
        await _seed_event_db(db_session, trip.id)

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=10,
            start_from_event_id=9999,
        )
        assert result == []

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_propagation_stops_when_gap_sufficient(self, mock_maps_factory, db_session):
        """Two events 2h apart; 30min shift leaves a 90min gap which is > travel time."""
        trip = await _seed_trip(db_session)
        ev1 = await _seed_event_db(
            db_session, trip.id, title="A",
            start_time=time(10, 0), end_time=time(11, 0),
            place_id="ChIJ_A",
        )
        await _seed_event_db(
            db_session, trip.id, title="B",
            start_time=time(13, 0), end_time=time(14, 0),
            place_id="ChIJ_B",
        )

        leg = MagicMock()
        leg.duration_s = 600  # 10 minutes travel
        route = MagicMock()
        route.legs = [leg]
        mock_maps = MagicMock()
        mock_maps.directions = AsyncMock(return_value=route)
        mock_maps_factory.return_value = mock_maps

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=30,
            start_from_event_id=ev1.id,
        )
        assert len(result) == 1  # only ev1 shifted, ev2 has enough buffer

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_propagation_cascades(self, mock_maps_factory, db_session):
        """Two back-to-back events; shifting the first cascades to the second."""
        trip = await _seed_trip(db_session)
        ev1 = await _seed_event_db(
            db_session, trip.id, title="A",
            start_time=time(10, 0), end_time=time(11, 0),
            place_id="ChIJ_A",
        )
        ev2 = await _seed_event_db(
            db_session, trip.id, title="B",
            start_time=time(11, 0), end_time=time(12, 0),
            place_id="ChIJ_B",
        )

        leg = MagicMock()
        leg.duration_s = 600  # 10 min travel
        route = MagicMock()
        route.legs = [leg]
        mock_maps = MagicMock()
        mock_maps.directions = AsyncMock(return_value=route)
        mock_maps_factory.return_value = mock_maps

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=15,
            start_from_event_id=ev1.id,
        )
        assert len(result) == 2
        assert result[0].start_time == time(10, 15)
        assert result[1].start_time >= time(11, 15)

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_trip_not_found_defaults_utc(self, mock_maps_factory, db_session):
        """When trip doesn't exist, engine should still work with UTC fallback."""
        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=9999, delta_minutes=10,
        )
        assert result == []

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_start_from_time_filters_events(self, mock_maps_factory, db_session):
        trip = await _seed_trip(db_session)
        await _seed_event_db(
            db_session, trip.id, title="Early",
            start_time=time(8, 0), end_time=time(9, 0),
        )
        await _seed_event_db(
            db_session, trip.id, title="Late",
            start_time=time(15, 0), end_time=time(16, 0),
        )

        mock_maps = MagicMock()
        mock_maps.directions = AsyncMock(return_value=None)
        mock_maps_factory.return_value = mock_maps

        from app.utils.tz import combine_in_tz
        cutoff = combine_in_tz(date(2025, 7, 1), time(14, 0), "UTC")

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=10,
            start_from_time=cutoff,
        )
        assert len(result) == 1
        assert result[0].title == "Late"

    @patch("app.services.smart_ripple.get_google_maps_service")
    async def test_no_future_events_returns_empty(self, mock_maps_factory, db_session):
        """All events are before start_from_time → nothing to shift."""
        trip = await _seed_trip(db_session)
        await _seed_event_db(
            db_session, trip.id, title="Past",
            start_time=time(8, 0), end_time=time(9, 0),
        )

        from app.utils.tz import combine_in_tz
        cutoff = combine_in_tz(date(2025, 7, 1), time(20, 0), "UTC")

        engine = SmartRippleEngine()
        result = await engine.shift_itinerary(
            db=db_session, trip_id=trip.id, delta_minutes=10,
            start_from_time=cutoff,
        )
        assert result == []
