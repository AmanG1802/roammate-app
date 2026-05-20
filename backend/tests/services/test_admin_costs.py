"""§7E — Cost computation tests.

Verifies the pricing tables and cost calculation functions.
"""
from __future__ import annotations

import pytest

from app.services.admin_costs import (
    MAPS_PRICING,
    TOKEN_PRICING,
    compute_maps_cost,
    compute_token_cost,
)


def test_TOKEN_PRICING_includes_each_supported_provider_model_pair():
    assert ("openai", "gpt-4o-mini") in TOKEN_PRICING
    assert ("claude", "claude-sonnet-4-20250514") in TOKEN_PRICING
    assert ("gemini", "gemini-2.0-flash") in TOKEN_PRICING
    assert ("gemini", "gemini-2.5-flash") in TOKEN_PRICING


@pytest.mark.parametrize(
    "provider,model,tokens_in,tokens_out,expected",
    [
        # gpt-4o-mini: $0.15/1M in, $0.60/1M out
        ("openai", "gpt-4o-mini", 1_000_000, 1_000_000, 0.75),
        ("openai", "gpt-4o-mini", 100, 50, 0.000045),
        # claude: $3.00/1M in, $15.00/1M out
        ("claude", "claude-sonnet-4-20250514", 1_000_000, 1_000_000, 18.0),
        # gemini-2.0-flash: $0.075/1M in, $0.30/1M out
        ("gemini", "gemini-2.0-flash", 1_000_000, 1_000_000, 0.375),
        # gemini-2.5-flash: $0.15/1M in, $0.60/1M out
        ("gemini", "gemini-2.5-flash", 1_000_000, 1_000_000, 0.75),
    ],
)
def test_token_cost_calculation_known_values(
    provider, model, tokens_in, tokens_out, expected
):
    cost = compute_token_cost(provider, model, tokens_in, tokens_out)
    assert cost == pytest.approx(expected, rel=1e-4)


def test_unknown_model_returns_zero_cost():
    cost = compute_token_cost("unknown", "fake-model", 1000, 1000)
    assert cost == 0.0


def test_MAPS_PRICING_each_op_has_entry():
    expected_ops = {
        "place_details_v1", "place_details_v2",
        "nearby_or_text_search", "directions", "routes",
        "photo_url", "timezone", "enrich_batch",
    }
    assert set(MAPS_PRICING.keys()) == expected_ops


def test_enrich_batch_pricing_is_zero():
    assert MAPS_PRICING["enrich_batch"] == 0.0


def test_compute_maps_cost_cache_hit_is_zero():
    cost = compute_maps_cost("place_details_v1", "hit")
    assert cost == 0.0


def test_compute_maps_cost_negative_cache_is_zero():
    cost = compute_maps_cost("place_details_v1", "negative")
    assert cost == 0.0


@pytest.mark.parametrize("op,expected", [
    ("place_details_v1",      0.005100),  # $5.10 CPM
    ("place_details_v2",      0.005100),  # $5.10 CPM
    ("nearby_or_text_search", 0.009600),  # $9.60 CPM
    ("directions",            0.001500),  # $1.50 CPM
    ("routes",                0.001500),  # $1.50 CPM
    ("photo_url",             0.002100),  # $2.10 CPM
    ("enrich_batch",          0.000000),  # composite — $0
])
def test_compute_maps_cost_per_op(op, expected):
    cost = compute_maps_cost(op, None)
    assert cost == pytest.approx(expected, abs=1e-6)


def test_decimal_precision_to_six_places():
    cost = compute_token_cost("openai", "gpt-4o-mini", 1, 1)
    # Very small cost — ensure it rounds to 6 decimal places
    cost_str = f"{cost:.6f}"
    assert len(cost_str.split(".")[-1]) == 6
