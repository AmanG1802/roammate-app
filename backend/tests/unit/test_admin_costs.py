"""Unit tests for app.services.admin_costs — cost computation functions.

Pure arithmetic with dictionary lookups, no DB or network.
"""
import pytest
from app.services.admin_costs import (
    compute_token_cost,
    compute_maps_cost,
    TOKEN_PRICING,
    MAPS_PRICING,
)


class TestComputeTokenCost:
    def test_compute_token_cost(self):
        # Test 1a - OpenAI gpt-4o-mini pricing: input 0.15/1M, output 0.60/1M
        cost = compute_token_cost("openai", "gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == round(0.15 + 0.60, 6)

        # Test 1b - Zero tokens returns zero cost
        cost = compute_token_cost("openai", "gpt-4o-mini", 0, 0)
        assert cost == 0.0

        # Test 1c - Unknown provider/model returns 0.0
        cost = compute_token_cost("unknown_provider", "unknown_model", 1000, 1000)
        assert cost == 0.0

        # Test 1d - Gemini 2.0 flash pricing
        cost = compute_token_cost("gemini", "gemini-2.0-flash", 1_000_000, 1_000_000)
        assert cost == round(0.075 + 0.30, 6)

        # Test 1e - Small token counts (typical single call)
        cost = compute_token_cost("openai", "gpt-4o-mini", 500, 200)
        expected = (500 / 1_000_000) * 0.15 + (200 / 1_000_000) * 0.60
        assert cost == round(expected, 6)

        # Test 1f - Claude pricing
        cost = compute_token_cost("claude", "claude-sonnet-4-20250514", 1000, 500)
        expected = (1000 / 1_000_000) * 3.00 + (500 / 1_000_000) * 15.00
        assert cost == round(expected, 6)

        # Test 1g - Result is rounded to 6 decimal places
        cost = compute_token_cost("openai", "gpt-4o-mini", 1, 1)
        assert isinstance(cost, float)
        str_cost = str(cost)
        if "." in str_cost:
            assert len(str_cost.split(".")[1]) <= 6

    @pytest.mark.parametrize("provider,model", list(TOKEN_PRICING.keys()))
    def test_all_known_providers(self, provider: str, model: str):
        # Test 1h - Every configured provider/model pair returns non-zero for non-zero tokens
        cost = compute_token_cost(provider, model, 10000, 10000)
        assert cost > 0


class TestComputeMapsCost:
    def test_compute_maps_cost(self):
        # Test 1a - Cache hit returns zero cost
        cost = compute_maps_cost("place_details_v1", "hit")
        assert cost == 0.0

        # Test 1b - Negative cache hit returns zero cost
        cost = compute_maps_cost("directions", "negative")
        assert cost == 0.0

        # Test 1c - Cache miss (None) incurs cost
        cost = compute_maps_cost("place_details_v1", None)
        expected = round(5.10 / 1000, 6)
        assert cost == expected

        # Test 1d - Unknown operation returns zero
        cost = compute_maps_cost("unknown_op", None)
        assert cost == 0.0

        # Test 1e - Directions cost (Essentials tier)
        cost = compute_maps_cost("directions", "miss")
        expected = round(1.50 / 1000, 6)
        assert cost == expected

        # Test 1f - enrich_batch is always free (composite op)
        cost = compute_maps_cost("enrich_batch", None)
        assert cost == 0.0

        # Test 1g - Photo URL cost (Enterprise tier)
        cost = compute_maps_cost("photo_url", None)
        expected = round(2.10 / 1000, 6)
        assert cost == expected

    @pytest.mark.parametrize("op", list(MAPS_PRICING.keys()))
    def test_all_ops_with_cache_hit(self, op: str):
        # Test 1h - Every known op returns 0 on cache hit
        assert compute_maps_cost(op, "hit") == 0.0

    @pytest.mark.parametrize("op,cpm", list(MAPS_PRICING.items()))
    def test_all_ops_with_miss(self, op: str, cpm: float):
        # Test 1i - Every known op returns cpm/1000 on miss
        cost = compute_maps_cost(op, None)
        assert cost == round(cpm / 1000, 6)
