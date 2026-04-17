"""Tests for /api/events/quick-add/{trip_id}."""
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from tests.conftest import create_trip


async def test_quick_add_success(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.quick_add.nlp_service.parse_quick_add",
        new=AsyncMock(return_value={
            "title": "Colosseum Tour",
            "start_iso": "2026-06-01T14:00:00",
            "duration_minutes": 90,
            "event_type": "activity",
        }),
    ), patch(
        "app.services.quick_add.google_maps_service.find_place",
        new=AsyncMock(return_value={
            "name": "Colosseum",
            "place_id": "c1",
            "geometry": {"location": {"lat": 41.89, "lng": 12.49}},
        }),
    ):
        resp = await client.post(
            f"/api/events/quick-add/{trip['id']}",
            json={"text": "Colosseum tour at 2pm"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Colosseum"
    assert data["event_type"] == "activity"


async def test_quick_add_non_member(
    client: AsyncClient, auth_headers, second_auth_headers
):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/events/quick-add/{trip['id']}",
        json={"text": "X"},
        headers=second_auth_headers,
    )
    assert resp.status_code == 403


async def test_quick_add_nlp_failure_surfaces_500(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    with patch(
        "app.services.quick_add.nlp_service.parse_quick_add",
        new=AsyncMock(side_effect=Exception("nlp down")),
    ):
        resp = await client.post(
            f"/api/events/quick-add/{trip['id']}",
            json={"text": "X"},
            headers=auth_headers,
        )
    assert resp.status_code == 500
