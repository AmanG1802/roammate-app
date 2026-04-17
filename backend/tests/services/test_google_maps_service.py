"""Unit tests for GoogleMapsService."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.google_maps import GoogleMapsService


async def test_no_key_returns_mock():
    svc = GoogleMapsService(api_key=None)
    result = await svc.find_place("Colosseum")
    assert result["name"] == "Colosseum"
    assert result["place_id"].startswith("mock_id_")
    assert result["geometry"]["location"] == {"lat": 41.8902, "lng": 12.4922}


async def test_with_key_ok_response():
    svc = GoogleMapsService(api_key="real")
    fake_resp = MagicMock()
    fake_resp.json.return_value = {
        "status": "OK",
        "candidates": [{"name": "Colosseum", "place_id": "c1",
                         "geometry": {"location": {"lat": 1, "lng": 2}}}],
    }
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=fake_resp)
    with patch("app.services.google_maps.httpx.AsyncClient", return_value=mock_client):
        result = await svc.find_place("Colosseum")
    assert result["name"] == "Colosseum"


async def test_with_key_non_ok_returns_none():
    svc = GoogleMapsService(api_key="real")
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"status": "ZERO_RESULTS", "candidates": []}
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=fake_resp)
    with patch("app.services.google_maps.httpx.AsyncClient", return_value=mock_client):
        result = await svc.find_place("nowhere")
    assert result is None


async def test_with_key_no_candidates_returns_none():
    svc = GoogleMapsService(api_key="real")
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"status": "OK", "candidates": []}
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=fake_resp)
    with patch("app.services.google_maps.httpx.AsyncClient", return_value=mock_client):
        result = await svc.find_place("nowhere")
    assert result is None
