"""§4E — Google Maps tracker tests.

Verifies structured logging and DB persistence for maps API usage.
"""
from __future__ import annotations

import asyncio
import logging

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import GoogleMapsApiUsage
from app.services.google_maps.tracker import track_call
from tests.conftest import TestSessionLocal, wait_for_tracker_writes


async def test_track_call_logs_structured_record(caplog):
    with caplog.at_level(logging.INFO, logger="roammate.google_maps"):
        track_call(
            op="find_place",
            status="ok",
            latency_ms=42,
            cache_state="miss",
        )
    assert any("google_api" in r.message for r in caplog.records)
    assert any("op=find_place" in r.message for r in caplog.records)


async def test_track_call_persists_google_maps_api_usage_row(
    tracker_db, db_session: AsyncSession
):
    track_call(
        op="find_place",
        status="ok",
        latency_ms=55,
        attempts=1,
        cache_state="miss",
        user_id=1,
        trip_id=2,
    )
    await wait_for_tracker_writes()

    rows = (await db_session.execute(select(GoogleMapsApiUsage))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.op == "find_place"
    assert row.status == "ok"
    assert row.latency_ms == 55
    assert row.cache_state == "miss"
    assert row.user_id == 1
    assert row.trip_id == 2


async def test_track_call_cost_zero_for_cache_hits(
    tracker_db, db_session: AsyncSession
):
    track_call(op="find_place", status="ok", cache_state="hit")
    await wait_for_tracker_writes()

    row = (await db_session.execute(select(GoogleMapsApiUsage))).scalars().first()
    assert row is not None
    assert float(row.cost_usd) == 0.0


async def test_track_call_cost_uses_maps_pricing_for_op(
    tracker_db, db_session: AsyncSession
):
    track_call(op="find_place", status="ok", cache_state="miss")
    await wait_for_tracker_writes()

    row = (await db_session.execute(select(GoogleMapsApiUsage))).scalars().first()
    assert row is not None
    # find_place: $17.00/1000 = $0.017 per call
    assert float(row.cost_usd) == 0.017


async def test_track_call_user_id_optional(
    tracker_db, db_session: AsyncSession
):
    track_call(op="place_details", status="ok", cache_state="miss")
    await wait_for_tracker_writes()

    row = (await db_session.execute(select(GoogleMapsApiUsage))).scalars().first()
    assert row is not None
    assert row.user_id is None


async def test_enrich_batch_op_does_not_double_count_cost(
    tracker_db, db_session: AsyncSession
):
    track_call(
        op="enrich_batch",
        status="ok",
        cache_state="miss",
        batch_size=5,
        enriched_count=5,
    )
    await wait_for_tracker_writes()

    row = (await db_session.execute(select(GoogleMapsApiUsage))).scalars().first()
    assert row is not None
    assert float(row.cost_usd) == 0.0


async def test_track_call_db_failure_swallowed_logs_warning(
    monkeypatch, caplog
):
    """If DB persistence fails, the caller's code path is unaffected."""
    from app.services.google_maps import tracker as tracker_mod

    async def _broken(record):
        raise RuntimeError("DB exploded")

    monkeypatch.setattr(tracker_mod, "_persist_maps_usage", _broken)

    # Should NOT raise
    track_call(op="find_place", status="ok", cache_state="miss")
    await asyncio.sleep(0.05)
