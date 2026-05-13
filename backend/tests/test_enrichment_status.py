"""Unit tests for EnrichmentSummary returned by enrich_items_with_summary()."""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx

from app.services.google_maps import MockMapService
from app.services.google_maps.base import EnrichmentSummary
from app.services.google_maps import cache as gmap_cache
from app.services.google_maps.breaker import breaker


@pytest.fixture(autouse=True)
async def _reset():
    gmap_cache.clear_all()
    breaker._state.failure_times.clear()
    breaker._state.opened_at = None
    breaker._state.half_open = False
    yield


# ── Full enrichment ──────────────────────────────────────────────────────────


async def test_mock_full_enrichment():
    """Mock service enriches all items → status='full'."""
    svc = MockMapService()
    items = [{"title": "Wat Pho"}, {"title": "Grand Palace"}]
    results, summary = await svc.enrich_items_with_summary(items)
    assert summary.status == "full"
    assert summary.total == 2
    assert summary.enriched == 2
    assert summary.skipped == 0
    assert summary.reason is None
    assert all(r.get("place_id") for r in results)


async def test_empty_items():
    svc = MockMapService()
    results, summary = await svc.enrich_items_with_summary([])
    assert summary.status == "full"
    assert summary.total == 0
    assert results == []


# ── Missing API key ──────────────────────────────────────────────────────────


async def test_missing_api_key_returns_none():
    """Non-mock service without API key → status='none', reason='missing_api_key'."""
    from app.services.google_maps.v1 import MapServiceV1
    svc = MapServiceV1(api_key="")
    items = [{"title": "X"}, {"title": "Y"}]
    results, summary = await svc.enrich_items_with_summary(items)
    assert summary.status == "none"
    assert summary.total == 2
    assert summary.enriched == 0
    assert summary.skipped == 2
    assert summary.reason == "missing_api_key"


# ── Breaker open ─────────────────────────────────────────────────────────────


async def test_breaker_open_returns_none():
    """When breaker is open, summary shows status='none', reason='breaker_open'."""
    from app.services.google_maps.v1 import MapServiceV1
    svc = MapServiceV1(api_key="test-key")

    with patch.object(breaker, "allow", new=AsyncMock(return_value=False)):
        items = [{"title": "A"}, {"title": "B"}]
        results, summary = await svc.enrich_items_with_summary(items)

    assert summary.status == "none"
    assert summary.reason == "breaker_open"
    assert summary.skipped == 2


# ── Partial enrichment ───────────────────────────────────────────────────────


async def test_partial_enrichment():
    """When some items are already enriched and the service enriches the rest, summary is 'full'."""
    svc = MockMapService()
    items = [
        {"title": "Already", "place_id": "already_enriched"},
        {"title": "Needs Enrichment"},
    ]
    results, summary = await svc.enrich_items_with_summary(items)
    assert summary.status == "full"
    assert summary.enriched == 2
    assert summary.skipped == 0


# ── Summary model ────────────────────────────────────────────────────────────


def test_enrichment_summary_serialization():
    s = EnrichmentSummary(
        status="partial", total=5, enriched=3, skipped=2, reason="network_error"
    )
    d = s.model_dump()
    assert d["status"] == "partial"
    assert d["reason"] == "network_error"
    assert d["total"] == 5


def test_enrichment_summary_no_reason_when_full():
    s = EnrichmentSummary(status="full", total=3, enriched=3, skipped=0)
    assert s.reason is None
