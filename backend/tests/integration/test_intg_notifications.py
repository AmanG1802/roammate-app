"""§11 Notifications — list, unread count, mark read, and event-driven emission."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.all_models import User, Trip, TripMember, Notification
from app.schemas.notification import NotificationType
from app.services import notification_service
from tests.conftest import create_trip, invite_and_accept


async def _inbox(client, headers):
    return (await client.get("/api/notifications", headers=headers)).json()


async def test_list_notifications_isolated_between_users(client: AsyncClient, auth_headers, second_auth_headers):
    await create_trip(client, auth_headers, name="A")
    alice = await _inbox(client, auth_headers)
    bob = await _inbox(client, second_auth_headers)
    assert any(n["type"] == "trip_created" for n in alice)
    assert all(n["type"] != "trip_created" for n in bob)


async def test_unread_count(client: AsyncClient, auth_headers):
    await create_trip(client, auth_headers)
    resp = await client.get("/api/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["unread"] >= 0


async def test_mark_one_as_read(client: AsyncClient, auth_headers):
    await create_trip(client, auth_headers)
    notifs = await _inbox(client, auth_headers)
    nid = notifs[0]["id"]
    resp = await client.post(f"/api/notifications/{nid}/read", headers=auth_headers)
    assert resp.status_code in (200, 204)


async def test_mark_all_as_read(client: AsyncClient, auth_headers):
    await create_trip(client, auth_headers)
    resp = await client.post("/api/notifications/mark-all-read", headers=auth_headers)
    assert resp.status_code in (200, 204)
    unread = (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["unread"]
    assert unread == 0


async def test_invite_notification_payload(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await client.post(f"/api/trips/{trip['id']}/invite", json={"email": "bob@test.com"}, headers=auth_headers)
    bob = await _inbox(client, second_auth_headers)
    assert any(n["type"] == "invite_received" for n in bob)


async def test_event_added_notification_excludes_actor(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(client, auth_headers, second_auth_headers, trip["id"], "bob@test.com")
    await client.post("/api/events", json={"trip_id": trip["id"], "title": "Dinner"}, headers=auth_headers)
    alice = [n for n in await _inbox(client, auth_headers) if n["type"] == "event_added"]
    bob = [n for n in await _inbox(client, second_auth_headers) if n["type"] == "event_added"]
    assert alice == []
    assert bob


# ── Notification service (DB level) ──────────────────────────────────────────

async def _make_user(db, email):
    u = User(email=email, name="U", hashed_password="x")
    db.add(u)
    await db.flush()
    return u


async def test_emit_creates_one_row_per_unique_recipient(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    await notification_service.emit(db_session, recipient_ids=[u1.id, u2.id, u1.id], type=NotificationType.TRIP_CREATED, payload={})
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert len(rows) == 2


async def test_emit_drops_none_recipients(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    await notification_service.emit(db_session, recipient_ids=[None, u1.id], type=NotificationType.TRIP_CREATED, payload={})
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert len(rows) == 1


async def test_emit_empty_recipients_is_noop(db_session):
    await notification_service.emit(db_session, recipient_ids=[], type=NotificationType.TRIP_CREATED, payload={})
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert rows == []


async def test_emit_disabled_type_is_noop(db_session, monkeypatch):
    monkeypatch.setitem(NotificationType.ENABLED, NotificationType.TRIP_CREATED, False)
    u1 = await _make_user(db_session, "a@x.com")
    await notification_service.emit(db_session, recipient_ids=[u1.id], type=NotificationType.TRIP_CREATED, payload={})
    await db_session.flush()
    rows = (await db_session.execute(select(Notification))).scalars().all()
    assert rows == []


async def test_trip_member_ids_accepted_only_by_default(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    u3 = await _make_user(db_session, "c@x.com")
    trip = Trip(name="T", created_by_id=u1.id)
    db_session.add(trip)
    await db_session.flush()
    db_session.add(TripMember(trip_id=trip.id, user_id=u1.id, role="admin", status="accepted"))
    db_session.add(TripMember(trip_id=trip.id, user_id=u2.id, role="view_only", status="accepted"))
    db_session.add(TripMember(trip_id=trip.id, user_id=u3.id, role="view_only", status="invited"))
    await db_session.flush()
    ids = await notification_service.trip_member_ids(db_session, trip.id)
    assert set(ids) == {u1.id, u2.id}


async def test_trip_member_ids_exclude_user(db_session):
    u1 = await _make_user(db_session, "a@x.com")
    u2 = await _make_user(db_session, "b@x.com")
    trip = Trip(name="T", created_by_id=u1.id)
    db_session.add(trip)
    await db_session.flush()
    db_session.add(TripMember(trip_id=trip.id, user_id=u1.id, role="admin", status="accepted"))
    db_session.add(TripMember(trip_id=trip.id, user_id=u2.id, role="view_only", status="accepted"))
    await db_session.flush()
    ids = await notification_service.trip_member_ids(db_session, trip.id, exclude_user_id=u1.id)
    assert ids == [u2.id]
