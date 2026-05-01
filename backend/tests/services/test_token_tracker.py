"""§1D — Token tracker tests.

Verifies structured logging, DB persistence via fire-and-forget task,
cost calculation, and error resilience.
"""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import TokenUsage
from app.services.llm.models.base import LLMResponse
from app.services.llm.token_tracker import track
from tests.conftest import TestSessionLocal, wait_for_tracker_writes


@pytest.fixture
def sample_response() -> LLMResponse:
    return LLMResponse(
        content="Hello world",
        input_tokens=100,
        output_tokens=50,
        model="gpt-4o-mini",
        provider="openai",
    )


async def test_track_writes_log_line(caplog, sample_response):
    with caplog.at_level(logging.INFO, logger="roammate.tokens"):
        track(sample_response, operation="chat", user_id=1, source="brainstorm")
    assert any("token_usage" in r.message for r in caplog.records)
    assert any("op=chat" in r.message for r in caplog.records)


async def test_track_persists_token_usage_row(
    tracker_db, db_session: AsyncSession, sample_response
):
    track(
        sample_response,
        operation="chat",
        user_id=None,
        trip_id=None,
        source="brainstorm",
    )
    await wait_for_tracker_writes()

    rows = (await db_session.execute(select(TokenUsage))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.tokens_in == 100
    assert row.tokens_out == 50
    assert row.tokens_total == 150
    assert row.provider == "openai"
    assert row.model == "gpt-4o-mini"
    assert row.op == "chat"
    assert row.source == "brainstorm"


async def test_track_cost_uses_pricing_table(
    tracker_db, db_session: AsyncSession
):
    response = LLMResponse(
        content="x",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        model="gpt-4o-mini",
        provider="openai",
    )
    track(response, operation="extract")
    await wait_for_tracker_writes()

    row = (await db_session.execute(select(TokenUsage))).scalars().first()
    assert row is not None
    # gpt-4o-mini: input $0.15/1M, output $0.60/1M → total $0.75
    expected = Decimal("0.75")
    assert Decimal(str(row.cost_usd)).quantize(Decimal("0.01")) == expected


async def test_track_unknown_model_zero_cost_no_crash(
    tracker_db, db_session: AsyncSession
):
    response = LLMResponse(
        content="x",
        input_tokens=500,
        output_tokens=200,
        model="unknown-model-xyz",
        provider="unknown-provider",
    )
    track(response, operation="chat")
    await wait_for_tracker_writes()

    row = (await db_session.execute(select(TokenUsage))).scalars().first()
    assert row is not None
    assert float(row.cost_usd) == 0.0


async def test_track_user_id_optional(
    tracker_db, db_session: AsyncSession, sample_response
):
    track(sample_response, operation="chat", user_id=None)
    await wait_for_tracker_writes()

    row = (await db_session.execute(select(TokenUsage))).scalars().first()
    assert row is not None
    assert row.user_id is None


async def test_track_db_error_does_not_break_caller(
    monkeypatch, sample_response
):
    """If persistence fails, the caller's code path continues normally."""
    from app.services.llm import token_tracker

    async def _broken_persist(record):
        raise RuntimeError("DB exploded")

    monkeypatch.setattr(token_tracker, "_persist_token_usage", _broken_persist)
    # Should NOT raise
    track(sample_response, operation="chat", user_id=1, source="test")
    await asyncio.sleep(0.05)
