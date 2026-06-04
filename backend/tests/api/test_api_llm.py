"""API tests for llm.py — POST /api/llm/plan-trip."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

NO_AUTH = {"Cookie": "", "Authorization": ""}


def _mock_dashboard_client():
    client = MagicMock()
    client.plan_trip = AsyncMock(return_value={
        "trip_name": "Paris Adventure",
        "start_date": "2025-06-01",
        "duration_days": 3,
        "items": [
            {"title": "Eiffel Tower", "category": "sightseeing"},
            {"title": "Louvre Museum", "category": "culture"},
        ],
        "destination_city": "Paris",
        "country_code": "FR",
        "user_output": "Here's your trip plan!",
    })
    return client


def _mock_maps_svc():
    svc = MagicMock()
    summary = MagicMock(status="full", total=2, enriched=2, skipped=0, reason=None)
    svc.enrich_items_with_summary = AsyncMock(return_value=(
        [
            {"title": "Eiffel Tower", "category": "sightseeing", "lat": 48.8584, "lng": 2.2945},
            {"title": "Louvre Museum", "category": "culture", "lat": 48.8606, "lng": 2.3376},
        ],
        summary,
    ))
    svc.timezone_for = AsyncMock(return_value="Europe/Paris")
    return svc


def _mock_geocode():
    from app.services.google_maps.base import LocationContext
    loc = LocationContext(lat=48.8566, lng=2.3522, country_code="FR")
    return AsyncMock(return_value=loc)


# ── POST /api/llm/plan-trip ───────────────────────────────────────────────

async def test_plan_trip_post(client: AsyncClient, auth_headers: dict):
    # Test 1a - POST - 200 OK - Plan trip with mocked LLM
    with patch("app.api.endpoints.llm.get_dashboard_client", return_value=_mock_dashboard_client()), \
         patch("app.api.endpoints.llm._get_enrichment_service", return_value=_mock_maps_svc()), \
         patch("app.api.endpoints.llm.get_google_maps_service", return_value=_mock_maps_svc()), \
         patch("app.api.endpoints.llm.geocode_city", new_callable=_mock_geocode):
        resp = await client.post("/api/llm/plan-trip", headers=auth_headers, json={
            "prompt": "Plan a 3-day trip to Paris",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "trip_name" in data
        assert "items" in data
        assert "duration_days" in data

    # Test 1b - POST - 502 Bad Gateway - LLM service unavailable
    mock_client = MagicMock()
    mock_client.plan_trip = AsyncMock(side_effect=Exception("LLM down"))
    with patch("app.api.endpoints.llm.get_dashboard_client", return_value=mock_client):
        resp = await client.post("/api/llm/plan-trip", headers=auth_headers, json={
            "prompt": "Plan a trip",
        })
        assert resp.status_code == 502

    # Test 1c - POST - 422 Unprocessable Entity - Missing prompt field
    resp = await client.post("/api/llm/plan-trip", headers=auth_headers, json={})
    assert resp.status_code == 422

    # Test 1d - POST - 401 Unauthorized - No auth
    resp = await client.post("/api/llm/plan-trip", json={"prompt": "Test"}, headers=NO_AUTH)
    assert resp.status_code == 401
