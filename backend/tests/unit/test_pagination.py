"""Unit tests for app.api.pagination — keyset cursor pagination helpers.

Pure encoding/decoding and logic, no DB.
"""
import pytest
import base64

from app.api.pagination import (
    is_paginated,
    clamp_limit,
    encode_cursor,
    decode_cursor,
    page_slice,
    DEFAULT_LIMIT,
    MAX_LIMIT,
)


class TestIsPaginated:
    def test_is_paginated(self):
        # Test 1a - Both None returns False (not paginated)
        assert is_paginated(None, None) is False

        # Test 1b - limit provided returns True
        assert is_paginated(10, None) is True

        # Test 1c - cursor provided returns True
        assert is_paginated(None, "abc") is True

        # Test 1d - Both provided returns True
        assert is_paginated(10, "abc") is True


class TestClampLimit:
    def test_clamp_limit(self):
        # Test 1a - None defaults to DEFAULT_LIMIT
        assert clamp_limit(None) == DEFAULT_LIMIT

        # Test 1b - Zero defaults to DEFAULT_LIMIT
        assert clamp_limit(0) == DEFAULT_LIMIT

        # Test 1c - Negative defaults to DEFAULT_LIMIT
        assert clamp_limit(-5) == DEFAULT_LIMIT

        # Test 1d - Normal value returns as-is
        assert clamp_limit(25) == 25

        # Test 1e - Value above MAX_LIMIT is clamped
        assert clamp_limit(500) == MAX_LIMIT

        # Test 1f - Value at MAX_LIMIT stays
        assert clamp_limit(MAX_LIMIT) == MAX_LIMIT

        # Test 1g - Value of 1 is valid
        assert clamp_limit(1) == 1


class TestEncodeCursor:
    def test_encode_cursor(self):
        # Test 1a - Encodes an integer ID to a URL-safe base64 string
        cursor = encode_cursor(42)
        assert isinstance(cursor, str)
        assert len(cursor) > 0

        # Test 1b - Decoding the result gives back the original ID
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        assert decoded == "42"

        # Test 1c - Large IDs work
        cursor = encode_cursor(999999)
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        assert decoded == "999999"


class TestDecodeCursor:
    def test_decode_cursor(self):
        # Test 1a - Decodes a valid cursor back to int
        cursor = encode_cursor(100)
        result = decode_cursor(cursor)
        assert result == 100

        # Test 1b - None returns None
        assert decode_cursor(None) is None

        # Test 1c - Empty string returns None
        assert decode_cursor("") is None

        # Test 1d - Invalid base64 returns None
        assert decode_cursor("!!!invalid!!!") is None

        # Test 1e - Valid base64 but non-integer content returns None
        bad_cursor = base64.urlsafe_b64encode(b"not_a_number").decode()
        assert decode_cursor(bad_cursor) is None

    def test_roundtrip(self):
        # Test 1f - Encode/decode roundtrip for various IDs
        for id_val in [1, 10, 100, 99999, 0]:
            assert decode_cursor(encode_cursor(id_val)) == id_val


class TestPageSlice:
    def test_page_slice(self):
        # Test 1a - Fewer rows than limit means no more pages
        rows = [1, 2, 3]
        page, has_more = page_slice(rows, limit=5)
        assert page == [1, 2, 3]
        assert has_more is False

        # Test 1b - Exactly limit rows means no more pages
        rows = [1, 2, 3, 4, 5]
        page, has_more = page_slice(rows, limit=5)
        assert page == [1, 2, 3, 4, 5]
        assert has_more is False

        # Test 1c - More rows than limit means has_more=True, sentinel dropped
        rows = [1, 2, 3, 4, 5, 6]  # limit+1 = 6
        page, has_more = page_slice(rows, limit=5)
        assert page == [1, 2, 3, 4, 5]
        assert has_more is True

        # Test 1d - Empty rows
        page, has_more = page_slice([], limit=10)
        assert page == []
        assert has_more is False
