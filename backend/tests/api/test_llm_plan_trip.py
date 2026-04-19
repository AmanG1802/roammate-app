"""Tests for /api/llm/plan-trip endpoint."""
from httpx import AsyncClient

from app.services.llm_client import _BANGKOK_FALLBACK_ITEMS


async def _register_and_get_headers(client: AsyncClient) -> dict:
    await client.post(
        "/api/users/register",
        json={"email": "llm@test.com", "password": "password123", "name": "LLM User"},
    )
    resp = await client.post(
        "/api/users/login",
        json={"email": "llm@test.com", "password": "password123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_plan_trip_returns_preview(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/llm/plan-trip",
        json={"prompt": "5-day Thailand itinerary"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trip_name"] == "Thailand Getaway"
    assert body["start_date"] is None
    assert body["duration_days"] == 3
    assert isinstance(body["items"], list)
    assert len(body["items"]) > 0


async def test_plan_trip_items_have_full_fields(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/llm/plan-trip",
        json={"prompt": "Bangkok trip"},
        headers=auth_headers,
    )
    item = resp.json()["items"][0]
    for field in (
        "title", "description", "category", "lat", "lng",
        "address", "photo_url", "rating", "price_level",
        "types", "opening_hours",
    ):
        assert field in item, f"Missing field: {field}"
        assert item[field] is not None, f"Field is None: {field}"


async def test_plan_trip_item_count(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/llm/plan-trip",
        json={"prompt": "Anything"},
        headers=auth_headers,
    )
    assert len(resp.json()["items"]) == len(_BANGKOK_FALLBACK_ITEMS)


async def test_plan_trip_requires_auth_401(client: AsyncClient):
    resp = await client.post(
        "/api/llm/plan-trip",
        json={"prompt": "Hello"},
    )
    assert resp.status_code == 401


async def test_plan_trip_missing_prompt_422(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/llm/plan-trip",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422
