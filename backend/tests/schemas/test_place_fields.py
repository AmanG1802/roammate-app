"""Regression tests for PlaceFields schema parity.

Every item type that represents a place/activity (Event, IdeaBinItem,
BrainstormItem, PlaceCard) must carry the shared PlaceFields so data
survives migration between bins and the timeline without field loss.
"""
import pytest

from app.schemas.place import PlaceFields
from app.schemas.event import EventBase, Event, EventCreate
from app.schemas.trip import IdeaBinItemBase, IdeaBinItem
from app.schemas.brainstorm import BrainstormItemBase, BrainstormItemOut
from app.schemas.concierge import PlaceCard


PLACE_FIELDS = set(PlaceFields.model_fields.keys())


# ── Inheritance verification ─────────────────────────────────────────────────

def test_event_base_inherits_place_fields():
    assert PLACE_FIELDS.issubset(set(EventBase.model_fields.keys()))


def test_idea_bin_item_base_inherits_place_fields():
    assert PLACE_FIELDS.issubset(set(IdeaBinItemBase.model_fields.keys()))


def test_brainstorm_item_base_inherits_place_fields():
    assert PLACE_FIELDS.issubset(set(BrainstormItemBase.model_fields.keys()))


def test_place_card_inherits_place_fields():
    assert PLACE_FIELDS.issubset(set(PlaceCard.model_fields.keys()))


# ── Concrete subclass field checks ───────────────────────────────────────────

def test_event_schema_has_place_fields():
    assert PLACE_FIELDS.issubset(set(Event.model_fields.keys()))


def test_event_create_has_place_fields():
    assert PLACE_FIELDS.issubset(set(EventCreate.model_fields.keys()))


def test_idea_bin_item_has_place_fields():
    assert PLACE_FIELDS.issubset(set(IdeaBinItem.model_fields.keys()))


def test_brainstorm_item_out_has_place_fields():
    assert PLACE_FIELDS.issubset(set(BrainstormItemOut.model_fields.keys()))


# ── Round-trip data preservation ─────────────────────────────────────────────

_FULL_PLACE_DATA = {
    "title": "Test Place",
    "description": "A lovely spot",
    "category": "Food & Dining",
    "place_id": "ChIJ_test123",
    "lat": 12.97,
    "lng": 77.59,
    "address": "123 Main St, Test City",
    "photo_url": "https://example.com/photo.jpg",
    "rating": 4.5,
    "price_level": 2,
    "types": ["cafe", "food", "establishment"],
    "time_category": "morning",
    "added_by": "Alice",
}


def test_place_fields_round_trip():
    """All shared fields survive serialization/deserialization."""
    obj = PlaceFields(**_FULL_PLACE_DATA)
    dumped = obj.model_dump()
    for key, val in _FULL_PLACE_DATA.items():
        assert dumped[key] == val, f"PlaceFields round-trip lost field: {key}"


def test_event_base_preserves_place_data():
    data = {**_FULL_PLACE_DATA, "trip_id": 1}
    obj = EventBase(**data)
    for key, val in _FULL_PLACE_DATA.items():
        assert getattr(obj, key) == val, f"EventBase lost field: {key}"


def test_idea_bin_item_base_preserves_place_data():
    obj = IdeaBinItemBase(**_FULL_PLACE_DATA)
    for key, val in _FULL_PLACE_DATA.items():
        assert getattr(obj, key) == val, f"IdeaBinItemBase lost field: {key}"


def test_brainstorm_item_base_preserves_place_data():
    obj = BrainstormItemBase(**_FULL_PLACE_DATA)
    for key, val in _FULL_PLACE_DATA.items():
        assert getattr(obj, key) == val, f"BrainstormItemBase lost field: {key}"


def test_place_card_preserves_place_data():
    obj = PlaceCard(**_FULL_PLACE_DATA)
    for key, val in _FULL_PLACE_DATA.items():
        assert getattr(obj, key) == val, f"PlaceCard lost field: {key}"


# ── Cross-schema model_dump compatibility ────────────────────────────────────

def test_place_card_dump_contains_all_place_fields():
    """PlaceCard.model_dump() must include every PlaceFields key."""
    obj = PlaceCard(**_FULL_PLACE_DATA)
    dumped = obj.model_dump()
    for key in PLACE_FIELDS:
        assert key in dumped, f"PlaceCard.model_dump() missing key: {key}"


def test_idea_bin_dump_contains_all_place_fields():
    obj = IdeaBinItemBase(**_FULL_PLACE_DATA)
    dumped = obj.model_dump()
    for key in PLACE_FIELDS:
        assert key in dumped, f"IdeaBinItemBase.model_dump() missing key: {key}"


def test_brainstorm_dump_contains_all_place_fields():
    obj = BrainstormItemBase(**_FULL_PLACE_DATA)
    dumped = obj.model_dump()
    for key in PLACE_FIELDS:
        assert key in dumped, f"BrainstormItemBase.model_dump() missing key: {key}"


# ── Minimal construction ─────────────────────────────────────────────────────

def test_place_fields_minimal():
    """Only title is required; everything else defaults to None."""
    obj = PlaceFields(title="Minimal")
    assert obj.title == "Minimal"
    assert obj.description is None
    assert obj.category is None
    assert obj.place_id is None
    assert obj.lat is None
    assert obj.lng is None
    assert obj.address is None
    assert obj.photo_url is None
    assert obj.rating is None
    assert obj.price_level is None
    assert obj.types is None
    assert obj.time_category is None
    assert obj.added_by is None


def test_place_card_requires_lat_lng_place_id():
    """PlaceCard overrides lat/lng/place_id to be required."""
    with pytest.raises(Exception):
        PlaceCard(title="Oops")
