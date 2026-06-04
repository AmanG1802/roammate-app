"""Unit tests for app.services.llm.dedup — brainstorm item deduplication.

Pure string normalization and Levenshtein distance logic, no DB or network.
"""
import pytest
from app.services.llm.dedup import _normalise, _levenshtein, deduplicate


class TestNormalise:
    def test_normalise(self):
        # Test 1a - Lowercase conversion
        assert _normalise("HELLO WORLD") == "hello world"

        # Test 1b - Accent stripping (NFKD decomposition)
        assert _normalise("Café Résumé") == "cafe resume"

        # Test 1c - Punctuation removal
        assert _normalise("Hello, World! (test)") == "hello world test"

        # Test 1d - Whitespace collapse
        assert _normalise("  too   many   spaces  ") == "too many spaces"

        # Test 1e - Empty string
        assert _normalise("") == ""

        # Test 1f - Already normalized string
        assert _normalise("hello") == "hello"

        # Test 1g - Special characters removed, whitespace collapsed
        assert _normalise("Wat Pho — Temple") == "wat pho temple"


class TestLevenshtein:
    def test_levenshtein(self):
        # Test 1a - Identical strings
        assert _levenshtein("hello", "hello") == 0

        # Test 1b - Single character difference
        assert _levenshtein("cat", "bat") == 1

        # Test 1c - Insertion
        assert _levenshtein("cat", "cats") == 1

        # Test 1d - Deletion
        assert _levenshtein("cats", "cat") == 1

        # Test 1e - Completely different
        assert _levenshtein("abc", "xyz") == 3

        # Test 1f - Empty vs non-empty
        assert _levenshtein("", "hello") == 5
        assert _levenshtein("hello", "") == 5

        # Test 1g - Both empty
        assert _levenshtein("", "") == 0

        # Test 1h - Transposition (not optimized — counts as 2 ops)
        assert _levenshtein("ab", "ba") == 2

        # Test 1i - Longer strings
        assert _levenshtein("kitten", "sitting") == 3


class TestDeduplicate:
    def test_deduplicate_by_place_id(self):
        # Test 1a - Exact place_id match removes duplicate
        new_items = [
            {"title": "Eiffel Tower", "place_id": "ChIJ_abc123"},
            {"title": "Louvre Museum", "place_id": "ChIJ_def456"},
        ]
        existing = [
            type("Item", (), {"title": "Eiffel Tower", "place_id": "ChIJ_abc123"})(),
        ]
        result = deduplicate(new_items, existing)
        assert len(result) == 1
        assert result[0]["title"] == "Louvre Museum"

    def test_deduplicate_by_exact_title(self):
        # Test 1b - Exact normalized title match removes duplicate
        new_items = [
            {"title": "Thip Samai Pad Thai", "place_id": None},
        ]
        existing = [
            type("Item", (), {"title": "Thip Samai Pad Thai", "place_id": None})(),
        ]
        result = deduplicate(new_items, existing)
        assert len(result) == 0

    def test_deduplicate_by_fuzzy_title(self):
        # Test 1c - Levenshtein distance <= 3 is considered duplicate
        new_items = [
            {"title": "Thip Samai Pad Tai", "place_id": None},  # "Tai" vs "Thai" = distance 1
        ]
        existing = [
            type("Item", (), {"title": "Thip Samai Pad Thai", "place_id": None})(),
        ]
        result = deduplicate(new_items, existing)
        assert len(result) == 0

    def test_deduplicate_fuzzy_above_threshold(self):
        # Test 1d - Title with distance > 3 is NOT a duplicate
        new_items = [
            {"title": "Completely Different Name", "place_id": None},
        ]
        existing = [
            type("Item", (), {"title": "Thip Samai Pad Thai", "place_id": None})(),
        ]
        result = deduplicate(new_items, existing)
        assert len(result) == 1

    def test_deduplicate_empty_new_items(self):
        # Test 1e - Empty new_items returns empty
        result = deduplicate([], [])
        assert result == []

    def test_deduplicate_empty_existing(self):
        # Test 1f - No existing items means all new items pass through
        new_items = [
            {"title": "Place A", "place_id": None},
            {"title": "Place B", "place_id": None},
        ]
        result = deduplicate(new_items, [])
        assert len(result) == 2

    def test_deduplicate_internal_dedup(self):
        # Test 1g - Duplicate titles within new_items are also deduplicated
        new_items = [
            {"title": "Same Place", "place_id": None},
            {"title": "Same Place", "place_id": None},
        ]
        result = deduplicate(new_items, [])
        assert len(result) == 1

    def test_deduplicate_no_title_passes_through(self):
        # Test 1h - Item with empty title passes through (not matchable)
        new_items = [
            {"title": "", "place_id": None},
        ]
        existing = [
            type("Item", (), {"title": "Something", "place_id": None})(),
        ]
        result = deduplicate(new_items, existing)
        assert len(result) == 1

    def test_deduplicate_dict_existing_items(self):
        # Test 1i - Existing items as dicts (not ORM objects) also work
        new_items = [
            {"title": "Eiffel Tower", "place_id": "ChIJ_abc"},
        ]
        existing = [
            {"title": "Eiffel Tower", "place_id": "ChIJ_abc"},
        ]
        result = deduplicate(new_items, existing)
        assert len(result) == 0

    def test_deduplicate_custom_threshold(self):
        # Test 1j - Custom distance_threshold changes behavior
        new_items = [
            {"title": "abcde", "place_id": None},
        ]
        existing = [
            type("Item", (), {"title": "abcXX", "place_id": None})(),  # distance = 2
        ]
        # threshold=1 should NOT match (distance 2 > 1)
        result = deduplicate(new_items, existing, distance_threshold=1)
        assert len(result) == 1
        # threshold=3 SHOULD match (distance 2 <= 3)
        result = deduplicate(new_items, existing, distance_threshold=3)
        assert len(result) == 0

    def test_deduplicate_case_insensitive(self):
        # Test 1k - Title matching is case-insensitive via normalization
        new_items = [
            {"title": "EIFFEL TOWER", "place_id": None},
        ]
        existing = [
            type("Item", (), {"title": "Eiffel Tower", "place_id": None})(),
        ]
        result = deduplicate(new_items, existing)
        assert len(result) == 0
