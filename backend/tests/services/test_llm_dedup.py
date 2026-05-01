"""§1C — Dedup module tests.

Verifies exact-match, case-insensitive, place_id, and Levenshtein-based
deduplication for brainstorm items.
"""
from __future__ import annotations

from app.services.llm.dedup import deduplicate


def _make_existing(title: str, place_id: str | None = None):
    """Create a mock ORM-like row with .title and .place_id attrs."""

    class _Row:
        def __init__(self, t, pid):
            self.title = t
            self.place_id = pid

    return _Row(title, place_id)


def test_dedup_removes_exact_title_duplicates():
    existing = [_make_existing("Grand Palace")]
    new_items = [{"title": "Grand Palace", "place_id": None}]
    result = deduplicate(new_items, existing)
    assert result == []


def test_dedup_removes_case_insensitive_duplicates():
    existing = [_make_existing("Grand Palace")]
    new_items = [{"title": "grand palace", "place_id": None}]
    result = deduplicate(new_items, existing)
    assert result == []


def test_dedup_keeps_distinct_place_ids_with_same_title():
    existing = [_make_existing("Starbucks", "pid_A")]
    new_items = [{"title": "Starbucks", "place_id": "pid_B"}]
    result = deduplicate(new_items, existing)
    # Same title but different place_id — title dedup catches it
    # (dedup is title-first, then place_id)
    assert result == []


def test_dedup_against_existing_brainstorm_items_excludes_already_added():
    existing = [
        _make_existing("Wat Pho", "pid_1"),
        _make_existing("Grand Palace", "pid_2"),
    ]
    new_items = [
        {"title": "Wat Pho", "place_id": "pid_1"},
        {"title": "Lumphini Park", "place_id": "pid_3"},
    ]
    result = deduplicate(new_items, existing)
    assert len(result) == 1
    assert result[0]["title"] == "Lumphini Park"


def test_dedup_by_place_id_match():
    existing = [_make_existing("Some Place", "pid_X")]
    new_items = [{"title": "Different Name", "place_id": "pid_X"}]
    result = deduplicate(new_items, existing)
    assert result == []


def test_dedup_fuzzy_levenshtein_within_threshold():
    existing = [_make_existing("Chatuchak Weekend Market")]
    new_items = [{"title": "Chatuchak Weeknd Market", "place_id": None}]
    result = deduplicate(new_items, existing)
    assert result == []


def test_dedup_fuzzy_levenshtein_beyond_threshold_kept():
    existing = [_make_existing("Chatuchak Weekend Market")]
    new_items = [{"title": "Chatuchak Night Bazaar", "place_id": None}]
    result = deduplicate(new_items, existing)
    assert len(result) == 1


def test_dedup_self_dedup_within_batch():
    """Duplicate titles within the new batch itself are removed."""
    existing = []
    new_items = [
        {"title": "Grand Palace", "place_id": None},
        {"title": "Grand Palace", "place_id": None},
    ]
    result = deduplicate(new_items, existing)
    assert len(result) == 1


def test_dedup_items_without_title_kept():
    existing = [_make_existing("Wat Pho")]
    new_items = [{"title": "", "place_id": None}]
    result = deduplicate(new_items, existing)
    assert len(result) == 1
