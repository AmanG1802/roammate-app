"""Pricing constants for cost attribution on admin dashboard.

Values are public list prices as of early 2025.  Update when pricing changes.
"""

# USD per 1 million tokens
TOKEN_PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("openai", "gpt-4o-mini"):              {"input": 0.15,  "output": 0.60},
    ("claude", "claude-sonnet-4-20250514"): {"input": 3.00,  "output": 15.00},
    ("gemini", "gemini-2.0-flash"):         {"input": 0.075, "output": 0.30},
    ("gemini", "gemini-2.5-flash"):         {"input": 0.15,  "output": 0.60},
}

# USD per 1,000 billable (non-cache) calls
MAPS_PRICING: dict[str, float] = {
    "find_place":    17.00,
    "place_details": 17.00,
    "photo_url":      7.00,
    "directions":    10.00,
    "enrich_batch":   0.00,  # composed of find_place + place_details — don't double-count
}


def compute_token_cost(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = TOKEN_PRICING.get((provider, model))
    if not pricing:
        return 0.0
    cost_in = (tokens_in / 1_000_000) * pricing["input"]
    cost_out = (tokens_out / 1_000_000) * pricing["output"]
    return round(cost_in + cost_out, 6)


def compute_maps_cost(op: str, cache_state: str | None) -> float:
    if cache_state in ("hit", "negative"):
        return 0.0
    per_thousand = MAPS_PRICING.get(op, 0.0)
    return round(per_thousand / 1000, 6)
