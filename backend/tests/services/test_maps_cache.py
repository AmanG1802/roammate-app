"""§4C — Cache behaviour tests for Google Maps service."""
from __future__ import annotations

import pytest

from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.cache import MISS


@pytest.fixture(autouse=True)
async def _clear_cache():
    gmap_cache.clear_all()
    yield
    gmap_cache.clear_all()


async def test_cache_find_place_miss_then_hit():
    val, state = await gmap_cache.get_find_place("Eiffel Tower")
    assert val is MISS
    assert state == "miss"

    await gmap_cache.set_find_place("Eiffel Tower", {"id": "e1"})
    val, state = await gmap_cache.get_find_place("Eiffel Tower")
    assert state == "hit"
    assert val["id"] == "e1"


async def test_cache_find_place_normalises_query():
    """Cache key is case-insensitive and whitespace-stripped."""
    await gmap_cache.set_find_place("  Grand Palace  ", {"id": "gp"})
    val, state = await gmap_cache.get_find_place("grand palace")
    assert state == "hit"
    assert val["id"] == "gp"


async def test_negative_cache_records_none_and_short_circuits():
    await gmap_cache.set_find_place("nonexistent_place", None)
    val, state = await gmap_cache.get_find_place("nonexistent_place")
    assert val is None
    assert state == "negative_hit"


async def test_cache_place_details_keyed_by_place_id_and_field_signature():
    await gmap_cache.set_place_details("pid_1", "sig_A", {"rating": 4.5})
    await gmap_cache.set_place_details("pid_1", "sig_B", {"rating": 3.0})

    val_a, _ = await gmap_cache.get_place_details("pid_1", "sig_A")
    val_b, _ = await gmap_cache.get_place_details("pid_1", "sig_B")
    assert val_a["rating"] == 4.5
    assert val_b["rating"] == 3.0


async def test_cache_v1_and_v2_entries_isolated():
    """Same place_id with different field signatures never collide."""
    await gmap_cache.set_place_details("pid_X", "v1_fields", {"source": "v1"})
    await gmap_cache.set_place_details("pid_X", "v2_fields", {"source": "v2"})

    v1_val, _ = await gmap_cache.get_place_details("pid_X", "v1_fields")
    v2_val, _ = await gmap_cache.get_place_details("pid_X", "v2_fields")
    assert v1_val["source"] == "v1"
    assert v2_val["source"] == "v2"


async def test_cache_directions_miss_then_hit():
    waypoints = ["place_A", "place_B"]
    val, state = await gmap_cache.get_directions(waypoints, "driving")
    assert val is MISS
    assert state == "miss"

    await gmap_cache.set_directions(waypoints, "driving", {"polyline": "abc"})
    val, state = await gmap_cache.get_directions(waypoints, "driving")
    assert state == "hit"
    assert val["polyline"] == "abc"


async def test_cache_directions_different_mode_isolated():
    waypoints = ["A", "B"]
    await gmap_cache.set_directions(waypoints, "driving", {"mode": "driving"})
    val, state = await gmap_cache.get_directions(waypoints, "walking")
    assert val is MISS
    assert state == "miss"


async def test_clear_all_resets_everything():
    await gmap_cache.set_find_place("test_q", {"id": "t1"})
    await gmap_cache.set_place_details("p1", "sig", {"val": 1})
    gmap_cache.clear_all()

    val1, _ = await gmap_cache.get_find_place("test_q")
    val2, _ = await gmap_cache.get_place_details("p1", "sig")
    assert val1 is MISS
    assert val2 is MISS
