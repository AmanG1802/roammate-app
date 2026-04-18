"""Unit tests for app.services.roles role gating helpers."""
import pytest
from fastapi import HTTPException

from app.models.all_models import User, Trip, TripMember
from app.services.roles import (
    get_trip_member, require_trip_member, require_trip_admin, require_vote_role,
)


async def _make_user(db, email) -> User:
    u = User(email=email, name="U", hashed_password="x")
    db.add(u)
    await db.flush()
    return u


async def _setup(db, role: str, status: str = "accepted"):
    u = await _make_user(db, f"{role}@x.com")
    trip = Trip(name="T", created_by_id=u.id)
    db.add(trip)
    await db.flush()
    m = TripMember(trip_id=trip.id, user_id=u.id, role=role, status=status)
    db.add(m)
    await db.flush()
    return trip, u


# ── get_trip_member ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_trip_member_returns_none_for_non_member(db_session):
    u = await _make_user(db_session, "x@x.com")
    trip = Trip(name="T", created_by_id=u.id)
    db_session.add(trip)
    await db_session.flush()
    m = await get_trip_member(db_session, trip.id, u.id)
    assert m is None


@pytest.mark.asyncio
async def test_get_trip_member_returns_none_for_invited_status(db_session):
    trip, u = await _setup(db_session, "admin", status="invited")
    m = await get_trip_member(db_session, trip.id, u.id)
    assert m is None


# ── require_trip_member ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_trip_member_raises_for_non_member(db_session):
    u = await _make_user(db_session, "x@x.com")
    trip = Trip(name="T", created_by_id=u.id)
    db_session.add(trip)
    await db_session.flush()
    with pytest.raises(HTTPException) as e:
        await require_trip_member(db_session, trip.id, u.id)
    assert e.value.status_code == 403


# ── require_trip_admin ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_trip_admin_accepts_admin(db_session):
    trip, u = await _setup(db_session, "admin")
    m = await require_trip_admin(db_session, trip.id, u.id)
    assert m.role == "admin"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["view_only", "view_with_vote"])
async def test_require_trip_admin_403_for_non_admin(db_session, role):
    trip, u = await _setup(db_session, role)
    with pytest.raises(HTTPException) as e:
        await require_trip_admin(db_session, trip.id, u.id)
    assert e.value.status_code == 403


# ── require_vote_role ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "view_with_vote"])
async def test_require_vote_role_accepts(db_session, role):
    trip, u = await _setup(db_session, role)
    m = await require_vote_role(db_session, trip.id, u.id)
    assert m.role == role


@pytest.mark.asyncio
async def test_require_vote_role_403_for_view_only(db_session):
    trip, u = await _setup(db_session, "view_only")
    with pytest.raises(HTTPException) as e:
        await require_vote_role(db_session, trip.id, u.id)
    assert e.value.status_code == 403
