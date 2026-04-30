"""Unit tests for IdeaBinService: time-hint extraction, stripping, ingest logic."""
from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select

from app.services.idea_bin import (
    idea_bin_service,
    _extract_time_hint,
    _strip_time_hint,
)
from app.models.all_models import IdeaBinItem, Trip, User


# ── Pure regex helpers ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "text,expected",
    [
        ("Colosseum at 2pm", "2pm"),
        ("Pantheon @ 14:00", "14:00"),
        ("Dinner at 8:30 pm", "8:30 pm"),
        ("just a title", None),
    ],
)
def test_extract_time_hint(text, expected):
    assert _extract_time_hint(text) == expected


def test_strip_time_hint_removes_time():
    assert _strip_time_hint("Colosseum at 2pm") == "Colosseum"


def test_strip_time_hint_no_change_if_no_time():
    assert _strip_time_hint("Colosseum") == "Colosseum"


def test_strip_time_hint_24h():
    assert _strip_time_hint("Pantheon 14:00") == "Pantheon"


# ── Service ingestion ─────────────────────────────────────────────────────────

@pytest.fixture
async def _seed_trip(db_session):
    user = User(email="u@x.com", name="U", hashed_password="h")
    db_session.add(user)
    await db_session.flush()
    trip = Trip(name="T", created_by_id=user.id)
    db_session.add(trip)
    await db_session.commit()
    return trip


async def test_ingest_creates_items_with_place(db_session, _seed_trip):
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value={
            # Places API (New) shape — see ``GoogleMapsService.find_place``.
            "id": "c1",
            "displayName": {"text": "Colosseum", "languageCode": "en"},
            "location": {"latitude": 1.0, "longitude": 2.0},
        }),
    ):
        items = await idea_bin_service.ingest_from_text(
            db=db_session, trip_id=_seed_trip.id, text="Colosseum at 2pm",
            added_by="Alice",
        )
    assert len(items) == 1
    assert items[0].title == "Colosseum"
    assert items[0].place_id == "c1"
    assert items[0].lat == 1.0
    assert items[0].time_hint == "2pm"
    assert items[0].added_by == "Alice"


async def test_ingest_falls_back_when_no_place(db_session, _seed_trip):
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        items = await idea_bin_service.ingest_from_text(
            db=db_session, trip_id=_seed_trip.id, text="Nowhere"
        )
    assert len(items) == 1
    assert items[0].title == "Nowhere"
    assert items[0].place_id is None


async def test_ingest_handles_google_exception(db_session, _seed_trip):
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(side_effect=Exception("api down")),
    ):
        items = await idea_bin_service.ingest_from_text(
            db=db_session, trip_id=_seed_trip.id, text="X"
        )
    assert len(items) == 1
    assert items[0].title == "X"


async def test_ingest_splits_commas_newlines(db_session, _seed_trip):
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        items = await idea_bin_service.ingest_from_text(
            db=db_session, trip_id=_seed_trip.id, text="A, B\nC"
        )
    titles = sorted(i.title for i in items)
    assert titles == ["A", "B", "C"]


async def test_ingest_empty_returns_empty(db_session, _seed_trip):
    items = await idea_bin_service.ingest_from_text(
        db=db_session, trip_id=_seed_trip.id, text=""
    )
    assert items == []
