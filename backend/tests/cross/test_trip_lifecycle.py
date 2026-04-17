"""End-to-end lifecycle tests across multiple services."""
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from tests.conftest import create_trip, invite_and_accept


async def test_full_trip_lifecycle(
    client: AsyncClient, auth_headers, second_auth_headers
):
    # 1. Alice creates trip
    trip = await create_trip(
        client, auth_headers, name="Italy", start_date="2026-06-01T00:00:00"
    )
    # 2. Alice invites Bob → Bob accepts
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com"
    )
    # 3. Bob can read the trip
    assert (
        await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    ).status_code == 200
    # 4. Alice adds a day
    resp = await client.post(
        f"/api/trips/{trip['id']}/days", json={"date": "2026-06-02"}, headers=auth_headers
    )
    assert resp.status_code == 201
    # 5. Alice ingests ideas
    with patch(
        "app.services.idea_bin.google_maps_service.find_place",
        new=AsyncMock(return_value=None),
    ):
        await client.post(
            f"/api/trips/{trip['id']}/ingest",
            json={"text": "Colosseum"},
            headers=auth_headers,
        )
    # 6. Alice adds an event
    await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "Lunch", "day_date": "2026-06-01",
              "start_time": "2026-06-01T13:00:00", "end_time": "2026-06-01T14:00:00"},
        headers=auth_headers,
    )
    # 7. Ripple
    resp = await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 30, "start_from_time": "2026-06-01T12:00:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # 8. Alice removes Bob
    members = (
        await client.get(f"/api/trips/{trip['id']}/members", headers=auth_headers)
    ).json()
    bob = [m for m in members if m["user"]["email"] == "bob@test.com"][0]
    resp = await client.delete(
        f"/api/trips/{trip['id']}/members/{bob['id']}", headers=auth_headers
    )
    assert resp.status_code == 204
    # Bob can no longer read
    assert (
        await client.get(f"/api/trips/{trip['id']}", headers=second_auth_headers)
    ).status_code == 403
    # 9. Alice deletes trip
    resp = await client.delete(f"/api/trips/{trip['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_view_only_cannot_mutate(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    await invite_and_accept(
        client, auth_headers, second_auth_headers, trip["id"], "bob@test.com",
        role="view_only",
    )
    # cannot invite
    resp = await client.post(
        f"/api/trips/{trip['id']}/invite",
        json={"email": "someone@x.com"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403
    # cannot add day
    resp = await client.post(
        f"/api/trips/{trip['id']}/days",
        json={"date": "2026-06-01"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_idor_across_trips(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip_a = await create_trip(client, auth_headers, name="Alice's")
    trip_b = await create_trip(client, second_auth_headers, name="Bob's")
    # Bob tries to read Alice's trip
    resp = await client.get(f"/api/trips/{trip_a['id']}", headers=second_auth_headers)
    assert resp.status_code == 403
    # Alice tries to get events for Bob's trip
    resp = await client.get(
        f"/api/events/?trip_id={trip_b['id']}", headers=auth_headers
    )
    assert resp.status_code == 403


async def test_ripple_then_day_delete_bin_reflects_shifted_time(
    client: AsyncClient, auth_headers
):
    trip = await create_trip(
        client, auth_headers, start_date="2026-06-01T00:00:00"
    )
    await client.post(
        "/api/events/",
        json={"trip_id": trip["id"], "title": "Lunch", "day_date": "2026-06-01",
              "start_time": "2026-06-01T13:00:00", "end_time": "2026-06-01T14:00:00"},
        headers=auth_headers,
    )
    # Ripple +60 min → now at 14:00
    await client.post(
        f"/api/events/ripple/{trip['id']}",
        json={"delta_minutes": 60, "start_from_time": "2026-06-01T12:00:00"},
        headers=auth_headers,
    )
    days = (
        await client.get(f"/api/trips/{trip['id']}/days", headers=auth_headers)
    ).json()
    await client.delete(
        f"/api/trips/{trip['id']}/days/{days[0]['id']}?items_action=bin",
        headers=auth_headers,
    )
    ideas = (
        await client.get(f"/api/trips/{trip['id']}/ideas", headers=auth_headers)
    ).json()
    assert ideas[0]["time_hint"] == "2pm"
