"""Roammate Plus entitlement service.

Single source of truth for what a user can do based on their subscription tier.

Free tier:
    - 2 active (upcoming, end_date >= today) trips at a time
    - 15 brainstorm AI messages per calendar month
    - Concierge chat is fully gated (read history allowed, POST blocked)
    - Offline maps disabled

Plus tier:
    - Unlimited active trips
    - Unlimited brainstorms (no counter increment)
    - Concierge chat allowed
    - Offline maps enabled

On cancellation / failed renewal we hard-enforce free limits (the user keeps
their data but the gates close). Past trips (end_date < today) always remain
viewable and never count against the active-trip cap.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.all_models import Trip, TripMember, UsageCounter, User

log = logging.getLogger(__name__)

# Feature codes returned to the client in 402 payloads. Keep these stable —
# the iOS app and web UI key off them to render contextual paywall copy.
Feature = Literal[
    "active_trips",
    "brainstorm_quota",
    "concierge",
    "offline_maps",
]

PLUS_FEATURES: set[Feature] = {"concierge", "offline_maps"}


def _current_period() -> str:
    """Return YYYY-MM in UTC. Counters reset on the 1st of every month."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _is_active(user: User) -> bool:
    """True if the user's subscription is currently effective.

    A `past_due` status keeps Plus active for the grace period we configure on
    the provider side; once the provider flips to `expired`/`canceled` the
    status here follows and `_is_active` returns False.
    """
    if user.subscription_tier != "plus":
        return False
    if user.subscription_status not in {"active", "past_due", "one_time"}:
        return False
    end = user.subscription_current_period_end
    if end is None:
        return True  # provider hasn't reported an end yet; trust the status
    return end >= datetime.now(timezone.utc)


@dataclass(frozen=True)
class Entitlement:
    tier: str                       # "free" | "plus"
    status: str                     # "none" | "active" | "past_due" | "canceled" | "expired"
    period_end: Optional[datetime]
    can_create_active_trip: bool
    can_use_concierge: bool
    can_use_offline_maps: bool
    brainstorm_remaining: Optional[int]   # None means unlimited
    active_trip_count: int
    active_trip_cap: Optional[int]        # None means unlimited
    brainstorm_used: int
    brainstorm_cap: Optional[int]         # None means unlimited

    def to_dto(self) -> dict:
        return {
            "tier": self.tier,
            "status": self.status,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "can_create_active_trip": self.can_create_active_trip,
            "can_use_concierge": self.can_use_concierge,
            "can_use_offline_maps": self.can_use_offline_maps,
            "brainstorm_remaining": self.brainstorm_remaining,
            "active_trip_count": self.active_trip_count,
            "active_trip_cap": self.active_trip_cap,
            "brainstorm_used": self.brainstorm_used,
            "brainstorm_cap": self.brainstorm_cap,
            "price_inr": settings.PLUS_MONTHLY_PRICE_INR,
            "onetime_price_inr": settings.PLUS_ONETIME_PRICE_INR,
            "onetime_duration_days": settings.PLUS_ONETIME_DURATION_DAYS,
        }


# ── Internal helpers ─────────────────────────────────────────────────────────


async def _active_trip_count(db: AsyncSession, user_id: int) -> int:
    """Number of trips the user is an accepted member of with end_date >= today.

    A trip is "active" if its end_date is today or in the future. Trips with
    no end_date are counted as active (planning-in-progress).
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(func.count(func.distinct(Trip.id)))
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(
            TripMember.user_id == user_id,
            TripMember.status == "accepted",
        )
        .where((Trip.end_date == None) | (Trip.end_date >= now))  # noqa: E711
    )
    return int((await db.execute(stmt)).scalar() or 0)


async def _brainstorm_usage(db: AsyncSession, user_id: int, period: str) -> int:
    stmt = select(UsageCounter.brainstorm_messages).where(
        UsageCounter.user_id == user_id,
        UsageCounter.period == period,
    )
    return int((await db.execute(stmt)).scalar() or 0)


# ── Public API ───────────────────────────────────────────────────────────────


async def get_entitlement(db: AsyncSession, user: User) -> Entitlement:
    """Compute the effective entitlement for a user."""
    is_plus = _is_active(user)
    active_count = await _active_trip_count(db, user.id)
    brainstorm_used = await _brainstorm_usage(db, user.id, _current_period())

    if is_plus:
        return Entitlement(
            tier="plus",
            status=user.subscription_status or "active",
            period_end=user.subscription_current_period_end,
            can_create_active_trip=True,
            can_use_concierge=True,
            can_use_offline_maps=True,
            brainstorm_remaining=None,
            active_trip_count=active_count,
            active_trip_cap=None,
            brainstorm_used=brainstorm_used,
            brainstorm_cap=None,
        )

    cap = settings.FREE_BRAINSTORM_MONTHLY_CAP
    trips_cap = settings.FREE_ACTIVE_TRIPS_CAP
    return Entitlement(
        tier="free",
        status=user.subscription_status or "none",
        period_end=user.subscription_current_period_end,
        can_create_active_trip=active_count < trips_cap,
        can_use_concierge=False,
        can_use_offline_maps=False,
        brainstorm_remaining=max(cap - brainstorm_used, 0),
        active_trip_count=active_count,
        active_trip_cap=trips_cap,
        brainstorm_used=brainstorm_used,
        brainstorm_cap=cap,
    )


def _raise_needs_plus(feature: Feature, **extra) -> None:
    payload = {"code": "needs_plus", "feature": feature, **extra}
    raise HTTPException(status_code=402, detail=payload)


def _is_tutorial(trip: Optional[Trip]) -> bool:
    return bool(trip is not None and getattr(trip, "is_tutorial", False))


async def enforce_active_trip(
    db: AsyncSession, user: User, *, is_tutorial: bool = False
) -> None:
    if is_tutorial:
        return
    ent = await get_entitlement(db, user)
    if not ent.can_create_active_trip:
        _raise_needs_plus(
            "active_trips",
            cap=ent.active_trip_cap,
            current=ent.active_trip_count,
        )


async def enforce_brainstorm(
    db: AsyncSession, user: User, *, trip: Optional[Trip] = None
) -> None:
    if _is_tutorial(trip):
        return
    ent = await get_entitlement(db, user)
    if ent.brainstorm_remaining is None:
        return  # Plus = unlimited
    if ent.brainstorm_remaining <= 0:
        _raise_needs_plus(
            "brainstorm_quota",
            cap=ent.brainstorm_cap,
            used=ent.brainstorm_used,
        )


async def enforce_concierge(
    db: AsyncSession, user: User, *, trip: Optional[Trip] = None
) -> None:
    if _is_tutorial(trip):
        return
    if not _is_active(user):
        _raise_needs_plus("concierge")


async def bump_brainstorm_counter(
    db: AsyncSession, user: User, *, trip: Optional[Trip] = None
) -> None:
    """Atomic upsert of the user's current-period counter.

    For Plus users this is a no-op (counter would be inaccurate after
    downgrade — and we don't enforce against it for Plus anyway).
    Tutorial trips also skip — they must not consume free-tier quota.
    """
    if _is_tutorial(trip):
        return
    if _is_active(user):
        return
    period = _current_period()
    stmt = (
        pg_insert(UsageCounter)
        .values(user_id=user.id, period=period, brainstorm_messages=1)
        .on_conflict_do_update(
            index_elements=["user_id", "period"],
            set_={
                "brainstorm_messages": UsageCounter.brainstorm_messages + 1,
                "updated_at": func.now(),
            },
        )
    )
    await db.execute(stmt)
