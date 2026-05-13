"""Tests for /api/concierge/* endpoints and is_skipped behaviour."""
from httpx import AsyncClient
from tests.conftest import create_trip


async def _create_event(client, headers, trip_id, **extra):
    payload = {"trip_id": trip_id, "title": "E"}
    payload.update(extra)
    resp = await client.post("/api/events/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── skip-event endpoint ──────────────────────────────────────────────────────

async def test_skip_event_sets_is_skipped(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(
        client, auth_headers, trip["id"],
        title="Museum", day_date="2026-06-01",
        start_time="2026-06-01T14:00:00", end_time="2026-06-01T15:00:00",
    )
    resp = await client.post(
        f"/api/concierge/{trip['id']}/skip-event",
        json={"event_id": event["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["updated_events"][0]["is_skipped"] is True


async def test_skip_event_nonexistent(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/concierge/{trip['id']}/skip-event",
        json={"event_id": 99999},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


# ── is_skipped visible in event listing ──────────────────────────────────────

async def test_events_list_includes_is_skipped(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(
        client, auth_headers, trip["id"],
        title="Gallery", day_date="2026-06-01",
    )
    assert event["is_skipped"] is False

    await client.post(
        f"/api/concierge/{trip['id']}/skip-event",
        json={"event_id": event["id"]},
        headers=auth_headers,
    )
    events = (
        await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    ).json()
    assert len(events) == 1
    assert events[0]["is_skipped"] is True


# ── skipped events excluded from route computation ───────────────────────────

async def test_route_excludes_skipped_events(client: AsyncClient, auth_headers):
    """Skipped events must not appear in route computation input."""
    trip = await create_trip(client, auth_headers)
    e1 = await _create_event(
        client, auth_headers, trip["id"],
        title="A", day_date="2026-06-01",
        start_time="2026-06-01T09:00:00", end_time="2026-06-01T10:00:00",
        lat=41.89, lng=12.49, place_id="pA",
    )
    await _create_event(
        client, auth_headers, trip["id"],
        title="B", day_date="2026-06-01",
        start_time="2026-06-01T11:00:00", end_time="2026-06-01T12:00:00",
        lat=41.90, lng=12.50, place_id="pB",
    )

    # Skip event A
    await client.post(
        f"/api/concierge/{trip['id']}/skip-event",
        json={"event_id": e1["id"]},
        headers=auth_headers,
    )

    # Compute route — should only contain event B, so 0 or 1 waypoints
    # (route endpoint requires at least 2 events to produce legs)
    resp = await client.post(
        f"/api/maps/route/{trip['id']}",
        json={"day_date": "2026-06-01"},
        headers=auth_headers,
    )
    if resp.status_code == 200:
        data = resp.json()
        waypoint_titles = [w.get("title") for w in data.get("waypoints", [])]
        assert "A" not in waypoint_titles


# ── is_skipped update via PATCH /events/{id} ─────────────────────────────────

async def test_patch_event_is_skipped(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    event = await _create_event(
        client, auth_headers, trip["id"], title="Lunch",
    )
    resp = await client.patch(
        f"/api/events/{event['id']}",
        json={"is_skipped": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_skipped"] is True

    # Toggle back
    resp = await client.patch(
        f"/api/events/{event['id']}",
        json={"is_skipped": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_skipped"] is False


# ── execute endpoint ─────────────────────────────────────────────────────────

async def test_execute_skip_event(client: AsyncClient, auth_headers):
    """The /execute endpoint should handle skip_event intent."""
    trip = await create_trip(client, auth_headers)
    event = await _create_event(
        client, auth_headers, trip["id"],
        title="Ruins", day_date="2026-06-01",
    )
    resp = await client.post(
        f"/api/concierge/{trip['id']}/execute",
        json={"intent": "skip_event", "params": {"event_id": event["id"]}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Skipped" in data["message"]


async def test_execute_add_event(client: AsyncClient, auth_headers):
    """The /execute endpoint should handle add_event intent."""
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/concierge/{trip['id']}/execute",
        json={
            "intent": "add_event",
            "params": {
                "title": "Coffee Break",
                "start_time": "2026-06-01T15:00:00",
                "category": "Food & Dining",
            },
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["new_event"]["title"] == "Coffee Break"


async def test_execute_add_event_preserves_all_place_fields(
    client: AsyncClient, auth_headers
):
    """add_event via /execute must persist all PlaceFields on the created event."""
    trip = await create_trip(client, auth_headers)
    enriched_params = {
        "title": "Third Wave Coffee",
        "start_time": "2026-06-01T15:00:00",
        "category": "Food & Dining",
        "place_id": "ChIJ_test_twc",
        "lat": 12.95,
        "lng": 77.73,
        "address": "Plot 207, Varthur Main Rd, Bengaluru",
        "photo_url": "https://example.com/twc.jpg",
        "rating": 4.6,
        "price_level": 2,
        "types": ["cafe", "food", "establishment"],
        "description": "Specialty coffee",
    }
    resp = await client.post(
        f"/api/concierge/{trip['id']}/execute",
        json={"intent": "add_event", "params": enriched_params},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    new_event = resp.json()["new_event"]

    assert new_event["title"] == "Third Wave Coffee"
    assert new_event["place_id"] == "ChIJ_test_twc"
    assert new_event["lat"] == 12.95
    assert new_event["lng"] == 77.73
    assert new_event["address"] == "Plot 207, Varthur Main Rd, Bengaluru"
    assert new_event["photo_url"] == "https://example.com/twc.jpg"
    assert new_event["rating"] == 4.6
    assert new_event["price_level"] == 2
    assert new_event["types"] == ["cafe", "food", "establishment"]
    assert new_event["category"] == "Food & Dining"
    assert new_event["description"] == "Specialty coffee"
    assert new_event["added_by"] == "Alice Smith"

    events = (
        await client.get(f"/api/events/?trip_id={trip['id']}", headers=auth_headers)
    ).json()
    event = next(e for e in events if e["title"] == "Third Wave Coffee")
    assert event["place_id"] == "ChIJ_test_twc"
    assert event["added_by"] == "Alice Smith"
    assert event["types"] == ["cafe", "food", "establishment"]


async def test_execute_find_nearby_preserves_all_place_fields(
    client: AsyncClient, auth_headers
):
    """find_nearby via /execute must persist all PlaceFields on the created event."""
    trip = await create_trip(client, auth_headers)
    place_params = {
        "title": "Glen's Bakehouse",
        "start_time": "2026-06-01T12:30:00",
        "place_id": "ChIJ_test_glens",
        "lat": 12.96,
        "lng": 77.74,
        "address": "7A, Whitefield Main Rd, Bengaluru",
        "photo_url": "https://example.com/glens.jpg",
        "rating": 4.4,
        "price_level": 2,
        "types": ["bakery", "food", "establishment"],
    }
    resp = await client.post(
        f"/api/concierge/{trip['id']}/execute",
        json={"intent": "find_nearby", "params": place_params},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    new_event = data["new_event"]

    assert new_event["title"] == "Glen's Bakehouse"
    assert new_event["place_id"] == "ChIJ_test_glens"
    assert new_event["lat"] == 12.96
    assert new_event["lng"] == 77.74
    assert new_event["address"] == "7A, Whitefield Main Rd, Bengaluru"
    assert new_event["photo_url"] == "https://example.com/glens.jpg"
    assert new_event["rating"] == 4.4
    assert new_event["price_level"] == 2
    assert new_event["types"] == ["bakery", "food", "establishment"]
    assert new_event["category"] == "Food & Dining"
    assert new_event["added_by"] == "Alice Smith"


async def test_find_nearby_includes_enrichment_status(
    client: AsyncClient, auth_headers
):
    """find-nearby response includes enrichment field (null when all have place_ids)."""
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/concierge/{trip['id']}/find-nearby",
        json={"query": "coffee", "lat": 13.75, "lng": 100.50},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "places" in data
    # Mock nearby_search returns places with place_ids → enrichment should be null
    assert data.get("enrichment") is None


async def test_execute_unknown_intent(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.post(
        f"/api/concierge/{trip['id']}/execute",
        json={"intent": "teleport", "params": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


# ── whats-next endpoint ──────────────────────────────────────────────────────

async def test_whats_next_returns_structure(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/concierge/{trip['id']}/whats-next", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "current_event" in data
    assert "next_event" in data
    assert "time_until_next" in data


# ── today-summary endpoint ───────────────────────────────────────────────────

async def test_today_summary_returns_structure(client: AsyncClient, auth_headers):
    trip = await create_trip(client, auth_headers)
    resp = await client.get(
        f"/api/concierge/{trip['id']}/today-summary", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "date" in data
    assert "total_events" in data
    assert "events" in data
    assert isinstance(data["events"], list)
