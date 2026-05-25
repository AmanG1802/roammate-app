"""API tests for health.py — GET /health"""

import pytest
from httpx import AsyncClient


async def test_health_check_get(client: AsyncClient):
    """One test function for GET /health."""

    # Test 1a - GET - 200 OK - Health check returns status ok
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
