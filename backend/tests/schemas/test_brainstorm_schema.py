"""Pydantic schema validation for brainstorm models."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.brainstorm import (
    BrainstormItemBase,
    BrainstormItemOut,
    BrainstormPromoteRequest,
    PlanTripResponse,
    BrainstormChatRequest,
)


def test_brainstorm_item_base_minimal():
    item = BrainstormItemBase(title="Test")
    assert item.title == "Test"
    assert item.description is None
    assert item.category is None
    assert item.lat is None
    assert item.types is None
    assert item.time_category is None


def test_brainstorm_item_out_from_attributes():
    data = {
        "id": 1,
        "trip_id": 10,
        "user_id": 5,
        "title": "Palace",
        "description": "Big palace",
        "category": "sight",
        "added_by": "AI",
        "created_at": datetime(2026, 4, 19, 12, 0),
    }
    out = BrainstormItemOut.model_validate(data)
    assert out.id == 1
    assert out.added_by == "AI"
    assert out.lat is None


def test_brainstorm_promote_request_none_means_all():
    req = BrainstormPromoteRequest()
    assert req.item_ids is None


def test_plan_trip_response_shape():
    resp = PlanTripResponse(
        trip_name="Thailand Getaway",
        start_date=None,
        duration_days=3,
        items=[BrainstormItemBase(title="Grand Palace")],
    )
    assert resp.trip_name == "Thailand Getaway"
    assert resp.duration_days == 3
    assert len(resp.items) == 1


def test_brainstorm_chat_request_requires_message():
    with pytest.raises(ValidationError):
        BrainstormChatRequest()
