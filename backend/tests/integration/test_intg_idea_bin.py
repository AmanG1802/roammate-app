"""§7 Idea Bin — list, ingest, delete, update, and service-level ingest tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.all_models import IdeaBinItem, Trip, User
from app.services.idea_bin import idea_bin_service
from tests.conftest import create_trip, invite_and_accept


async def _ingest(client, headers, trip_id, text="Colosseum"):
    r = await client.post(f"/api/trips/{trip_id}/ingest", json={"text": text}, headers=headers)
    return r.json()


async def test_list_ideas_for_trip(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    await _ingest(client, auth_headers, trip["id"])
    resp = await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_list_ideas_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(f"/api/trips/{trip['id']}/ideas", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_ingest_ideas_bulk(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    items = await _ingest(client, auth_headers, trip["id"], "A, B, C")
    assert len(items) >= 3


async def test_ingest_ideas_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(f"/api/trips/{trip['id']}/ingest", json={"text": "X"}, headers=second_auth_headers)
    assert resp.status_code == 403


async def test_delete_idea(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    items = await _ingest(client, auth_headers, trip["id"])
    resp = await client.delete(f"/api/trips/{trip['id']}/ideas/{items[0]['id']}", headers=auth_headers)
    assert resp.status_code in (200, 204)


async def test_delete_idea_non_member_403(client: AsyncClient, auth_headers, second_auth_headers):
    trip = await create_trip(client, auth_headers)
    items = await _ingest(client, auth_headers, trip["id"])
    resp = await client.delete(f"/api/trips/{trip['id']}/ideas/{items[0]['id']}", headers=second_auth_headers)
    assert resp.status_code == 403


async def test_delete_nonexistent_idea_404(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.delete(f"/api/trips/{trip['id']}/ideas/999999", headers=auth_headers)
    assert resp.status_code == 404


# ── IdeaBinService ────────────────────────────────────────────────────────────

async def test_idea_bin_service_ingest_from_text(db_session):
    user = User(email="u@x.com", name="U", hashed_password="h")
    db_session.add(user)
    await db_session.flush()
    trip = Trip(name="T", created_by_id=user.id)
    db_session.add(trip)
    await db_session.commit()

    with patch("app.services.idea_bin.google_maps_service.find_place", new=AsyncMock(return_value=None)):
        items = await idea_bin_service.ingest_from_text(db=db_session, trip_id=trip.id, text="A, B\nC")
    titles = sorted(i.title for i in items)
    assert titles == ["A", "B", "C"]


async def test_idea_bin_service_maps_failure_fallback(db_session):
    user = User(email="u@x.com", name="U", hashed_password="h")
    db_session.add(user)
    await db_session.flush()
    trip = Trip(name="T", created_by_id=user.id)
    db_session.add(trip)
    await db_session.commit()

    with patch("app.services.idea_bin.google_maps_service.find_place", new=AsyncMock(side_effect=Exception("boom"))):
        items = await idea_bin_service.ingest_from_text(db=db_session, trip_id=trip.id, text="X")
    assert len(items) == 1
    assert items[0].title == "X"
