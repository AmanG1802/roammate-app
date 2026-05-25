"""§2 Billing & Entitlements — entitlement checks, usage counters, and tier enforcement."""
from __future__ import annotations

from datetime import datetime, timedelta, date, timezone

import pytest
from sqlalchemy import select

from app.models.all_models import User, Trip, TripMember, UsageCounter
from app.services.entitlements import (
    get_entitlement,
    enforce_active_trip,
    enforce_brainstorm,
    enforce_concierge,
    bump_brainstorm_counter,
)


async def _make_user(db, email, tier="free", status=None, **kw) -> User:
    u = User(
        email=email, name="U", hashed_password="h",
        subscription_tier=tier,
        subscription_status=status,
        **kw,
    )
    db.add(u)
    await db.flush()
    return u


async def _make_trip(db, creator_id, **kw) -> Trip:
    t = Trip(name="T", created_by_id=creator_id, **kw)
    db.add(t)
    await db.flush()
    m = TripMember(trip_id=t.id, user_id=creator_id, role="admin", status="accepted")
    db.add(m)
    await db.flush()
    return t


# ── Entitlement defaults ─────────────────────────────────────────────────────

async def test_free_user_entitlement_defaults(db_session):
    u = await _make_user(db_session, "free@x.com")
    await db_session.commit()
    ent = await get_entitlement(db_session, u)
    assert ent.tier == "free"
    assert ent.can_use_concierge is False
    assert ent.brainstorm_remaining is not None and ent.brainstorm_remaining > 0
    assert ent.active_trip_cap is not None and ent.active_trip_cap > 0


async def test_plus_user_entitlement_unlimited(db_session):
    u = await _make_user(
        db_session, "plus@x.com", tier="plus", status="active",
        subscription_current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    await db_session.commit()
    ent = await get_entitlement(db_session, u)
    assert ent.tier == "plus"
    assert ent.can_use_concierge is True
    assert ent.brainstorm_remaining is None


async def test_expired_plus_reverts_to_free(db_session):
    u = await _make_user(
        db_session, "expired@x.com", tier="plus", status="active",
        subscription_current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    await db_session.commit()
    ent = await get_entitlement(db_session, u)
    assert ent.tier == "free"


async def test_past_due_status_keeps_plus_active(db_session):
    u = await _make_user(
        db_session, "pastdue@x.com", tier="plus", status="past_due",
        subscription_current_period_end=datetime.now(timezone.utc) + timedelta(days=5),
    )
    await db_session.commit()
    ent = await get_entitlement(db_session, u)
    assert ent.tier == "plus"


# ── Active trip cap ──────────────────────────────────────────────────────────

async def test_active_trip_count_excludes_past_trips(db_session):
    u = await _make_user(db_session, "u@x.com")
    past = date.today() - timedelta(days=10)
    await _make_trip(db_session, u.id, end_date=past)
    await db_session.commit()
    ent = await get_entitlement(db_session, u)
    assert ent.active_trip_count == 0


async def test_active_trip_count_includes_null_end_date(db_session):
    u = await _make_user(db_session, "u@x.com")
    await _make_trip(db_session, u.id, end_date=None)
    await db_session.commit()
    ent = await get_entitlement(db_session, u)
    assert ent.active_trip_count == 1


# ── Enforce caps ─────────────────────────────────────────────────────────────

async def test_enforce_active_trip_allows_tutorial(db_session):
    u = await _make_user(db_session, "u@x.com")
    await _make_trip(db_session, u.id)
    await _make_trip(db_session, u.id)
    await db_session.commit()
    await enforce_active_trip(db_session, u, is_tutorial=True)


# ── Brainstorm counter ───────────────────────────────────────────────────────

async def test_bump_brainstorm_counter_increments(db_session):
    u = await _make_user(db_session, "u@x.com")
    t = await _make_trip(db_session, u.id)
    await db_session.commit()
    await bump_brainstorm_counter(db_session, u, trip=t)
    await db_session.commit()
    row = (await db_session.execute(select(UsageCounter).where(UsageCounter.user_id == u.id))).scalars().first()
    assert row is not None
    assert row.brainstorm_messages >= 1


async def test_bump_brainstorm_counter_noop_for_plus(db_session):
    u = await _make_user(
        db_session, "plus@x.com", tier="plus", status="active",
        subscription_current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    t = await _make_trip(db_session, u.id)
    await db_session.commit()
    await bump_brainstorm_counter(db_session, u, trip=t)
    await db_session.commit()
    row = (await db_session.execute(select(UsageCounter).where(UsageCounter.user_id == u.id))).scalars().first()
    assert row is None


async def test_bump_brainstorm_counter_noop_for_tutorial(db_session):
    u = await _make_user(db_session, "u@x.com")
    t = await _make_trip(db_session, u.id, is_tutorial=True)
    await db_session.commit()
    await bump_brainstorm_counter(db_session, u, trip=t)
    await db_session.commit()
    row = (await db_session.execute(select(UsageCounter).where(UsageCounter.user_id == u.id))).scalars().first()
    assert row is None
