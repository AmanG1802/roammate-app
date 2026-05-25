"""Unit tests for app.services.vote_tally — vote aggregation logic.

The tally_votes function requires a DB session for the actual query, but
we test its early-return logic (empty target_ids) which is pure.
The SQL construction is validated in integration tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.vote_tally import tally_votes


class TestTallyVotes:
    @pytest.mark.asyncio
    async def test_empty_target_ids_returns_empty_dict(self):
        # Test 1a - Empty target_ids short-circuits to {}
        db = MagicMock()
        result = await tally_votes(db, MagicMock, MagicMock(), [], user_id=1)
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_list_does_not_query_db(self):
        # Test 1b - No DB call is made when target_ids is empty
        db = MagicMock()
        db.execute = AsyncMock()
        await tally_votes(db, MagicMock, MagicMock(), [], user_id=1)
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_sequence_treated_as_empty(self):
        # Test 1c - Passing an empty tuple also returns {}
        db = MagicMock()
        result = await tally_votes(db, MagicMock, MagicMock(), (), user_id=42)
        assert result == {}
