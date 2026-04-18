"""Unit tests for app.services.notification_service."""
import pytest
from sqlalchemy import select

from app.models.all_models import User, Trip, TripMember, Notification
from app.services import notification_service
from app.schemas.notification import NotificationType


async def _make_user(db, email, name="User") -> User:
    u = User(email=email, name=name, hashed_password="x")
    db.add(u)
    await db.flush()
    return u


async def _make_trip(db, creator_id) -> Trip:
    t = Trip(name="Trip", created_by_id=creator_id)
    db.add(t)
    await db.flush()
    return t


async def _add_member(db, trip_id, user_id, role="admin", status="accepted") -> TripMember:
    m = TripMember(trip_id=trip_id, user_id=user_id, role=role, status=status)
    db.add(m)
    await db.flush()
    return m


# ── emit() ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_creates_one_row_per_unique_recipient(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    await notification_service.emit(
        db_session,
        recipient_ids=[u1.id, u2.id, u1.id],  # duplicate u1
        type=NotificationType.TRIP_CREATED,
        payload={"trip_name": "T"},
    )
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_emit_drops_none_recipients(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    await notification_service.emit(
        db_session,
        recipient_ids=[None, u1.id, None],
        type=NotificationType.TRIP_CREATED,
        payload={},
    )
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert len(rows) == 1
    assert rows[0].user_id == u1.id


@pytest.mark.asyncio
async def test_emit_empty_recipients_is_noop(db_session):
    await notification_service.emit(
        db_session,
        recipient_ids=[],
        type=NotificationType.TRIP_CREATED,
        payload={},
    )
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_emit_persists_all_fields(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    actor = await _make_user(db_session, "b@x.com")
    await notification_service.emit(
        db_session,
        recipient_ids=[u1.id],
        type=NotificationType.TRIP_CREATED,
        payload={"trip_name": "Rome", "meta": [1, 2]},
        actor_id=actor.id,
        trip_id=42,
        group_id=7,
    )
    await db_session.flush()
    n = (await db_session.execute(select(Notification))).scalars().first()
    assert n.user_id == u1.id
    assert n.actor_id == actor.id
    assert n.trip_id == 42
    assert n.group_id == 7
    assert n.payload == {"trip_name": "Rome", "meta": [1, 2]}


@pytest.mark.asyncio
async def test_emit_disabled_type_is_noop(db_session, monkeypatch):
    monkeypatch.setitem(NotificationType.ENABLED, NotificationType.TRIP_CREATED, False)
    u1 = await _make_user(db_session, "a@x.com")
    await notification_service.emit(
        db_session,
        recipient_ids=[u1.id],
        type=NotificationType.TRIP_CREATED,
        payload={},
    )
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_is_enabled_unknown_type_defaults_true():
    assert NotificationType.is_enabled("does_not_exist_nope") is True


# ── trip_member_ids ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trip_member_ids_accepted_only_by_default(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    u3 = await _make_user(db_session, "c@x.com")
    trip = await _make_trip(db_session, u1.id)
    await _add_member(db_session, trip.id, u1.id, "admin", "accepted")
    await _add_member(db_session, trip.id, u2.id, "view_only", "accepted")
    await _add_member(db_session, trip.id, u3.id, "view_only", "invited")

    ids = await notification_service.trip_member_ids(db_session, trip.id)
    assert set(ids) == {u1.id, u2.id}


@pytest.mark.asyncio
async def test_trip_member_ids_accepted_only_false_includes_invited(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    trip = await _make_trip(db_session, u1.id)
    await _add_member(db_session, trip.id, u1.id, "admin", "accepted")
    await _add_member(db_session, trip.id, u2.id, "view_only", "invited")

    ids = await notification_service.trip_member_ids(db_session, trip.id, accepted_only=False)
    assert set(ids) == {u1.id, u2.id}


@pytest.mark.asyncio
async def test_trip_member_ids_exclude_user(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    trip = await _make_trip(db_session, u1.id)
    await _add_member(db_session, trip.id, u1.id, "admin", "accepted")
    await _add_member(db_session, trip.id, u2.id, "view_only", "accepted")

    ids = await notification_service.trip_member_ids(db_session, trip.id, exclude_user_id=u1.id)
    assert ids == [u2.id]


@pytest.mark.asyncio
async def test_all_trip_member_ids_includes_caller(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    trip = await _make_trip(db_session, u1.id)
    await _add_member(db_session, trip.id, u1.id, "admin", "accepted")
    await _add_member(db_session, trip.id, u2.id, "view_only", "accepted")

    ids = await notification_service.all_trip_member_ids(db_session, trip.id)
    assert set(ids) == {u1.id, u2.id}
