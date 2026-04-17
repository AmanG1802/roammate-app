"""Unit tests for QuickAddService."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import pytest

from app.services.quick_add import quick_add_service
from app.models.all_models import Trip, User


@pytest.fixture
async def _seeded(db_session):
    user = User(email="u@x.com", name="U", hashed_password="h")
    db_session.add(user)
    await db_session.flush()
    trip = Trip(name="T", created_by_id=user.id)
    db_session.add(trip)
    await db_session.commit()
    return trip


async def test_quick_add_with_nlp_time(db_session, _seeded):
    with patch(
        "app.services.quick_add.nlp_service.parse_quick_add",
        new=AsyncMock(return_value={
            "title": "Colosseum",
            "start_iso": "2026-06-01T14:00:00",
            "duration_minutes": 60,
            "event_type": "activity",
        }),
    ), patch(
        "app.services.quick_add.google_maps_service.find_place",
        new=AsyncMock(return_value={
            "name": "Colosseum", "place_id": "c1",
            "geometry": {"location": {"lat": 41.0, "lng": 12.0}},
        }),
    ):
        event = await quick_add_service.process_text(
            db=db_session, trip_id=_seeded.id, text="Colosseum at 2pm"
        )
    assert event.title == "Colosseum"
    assert event.start_time == datetime(2026, 6, 1, 14, 0)
    assert event.end_time == datetime(2026, 6, 1, 15, 0)
    assert event.place_id == "c1"
    assert event.event_type == "activity"


async def test_quick_add_default_duration(db_session, _seeded):
    with patch(
        "app.services.quick_add.nlp_service.parse_quick_add",
        new=AsyncMock(return_value={
            "title": "X", "start_iso": "2026-06-01T10:00:00",
            # no duration_minutes → default 60
        }),
    ), patch(
        "app.services.quick_add.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        event = await quick_add_service.process_text(
            db=db_session, trip_id=_seeded.id, text="X"
        )
    assert event.end_time - event.start_time == timedelta(minutes=60)


async def test_quick_add_without_start_iso_uses_today_10am(db_session, _seeded):
    with patch(
        "app.services.quick_add.nlp_service.parse_quick_add",
        new=AsyncMock(return_value={"title": "X"}),
    ), patch(
        "app.services.quick_add.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        event = await quick_add_service.process_text(
            db=db_session, trip_id=_seeded.id, text="X"
        )
    assert event.start_time.hour == 10
    assert event.start_time.minute == 0


async def test_quick_add_gmaps_exception_falls_back(db_session, _seeded):
    """After fix, GMaps errors are caught."""
    with patch(
        "app.services.quick_add.nlp_service.parse_quick_add",
        new=AsyncMock(return_value={
            "title": "Place", "start_iso": "2026-06-01T10:00:00",
        }),
    ), patch(
        "app.services.quick_add.google_maps_service.find_place",
        new=AsyncMock(side_effect=Exception("down")),
    ):
        event = await quick_add_service.process_text(
            db=db_session, trip_id=_seeded.id, text="Place"
        )
    assert event.title == "Place"
    assert event.place_id is None


async def test_quick_add_default_event_type(db_session, _seeded):
    with patch(
        "app.services.quick_add.nlp_service.parse_quick_add",
        new=AsyncMock(return_value={
            "title": "X", "start_iso": "2026-06-01T10:00:00",
        }),
    ), patch(
        "app.services.quick_add.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        event = await quick_add_service.process_text(
            db=db_session, trip_id=_seeded.id, text="X"
        )
    assert event.event_type == "activity"
