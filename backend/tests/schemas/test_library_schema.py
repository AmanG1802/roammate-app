"""Pydantic validation for library schemas (tags, copy request)."""
import pytest
from pydantic import ValidationError

from app.schemas.library import TagList, CopyIdeaRequest


def test_tag_list_lowercases_and_strips():
    t = TagList(tags=["  Food  ", "Museum"])
    assert t.tags == ["food", "museum"]


def test_tag_list_dedupes_case_insensitive():
    t = TagList(tags=["Food", "FOOD", "food"])
    assert t.tags == ["food"]


def test_tag_list_filters_empty_and_whitespace():
    t = TagList(tags=["", "   ", "food"])
    assert t.tags == ["food"]


def test_tag_list_preserves_first_occurrence_order():
    t = TagList(tags=["dessert", "food", "Dessert"])
    assert t.tags == ["dessert", "food"]


def test_tag_list_empty_list_ok():
    assert TagList(tags=[]).tags == []


def test_copy_idea_request_requires_target():
    with pytest.raises(ValidationError):
        CopyIdeaRequest()  # type: ignore[call-arg]


def test_copy_idea_request_accepts_int():
    assert CopyIdeaRequest(target_trip_id=42).target_trip_id == 42
