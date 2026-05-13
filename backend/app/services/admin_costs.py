"""Pricing constants for cost attribution on admin dashboard.

India pricing (CPM = cost per 1,000 billable events, USD).
Source: docs/google-maps-india-pricing.md — effective March 1, 2025.

Prices reflect the LOWEST tier we hit given our minimum-cost config:
    GOOGLE_MAPS_API_VERSION = "v1"  (legacy)
    GOOGLE_MAPS_FETCH_PHOTOS = False
    GOOGLE_MAPS_FETCH_RATING = False
    GOOGLE_MAPS_USE_NEARBY_API = False  (Text Search with locationBias)

When config flags change, the billed SKU escalates — see inline comments.
"""

# USD per 1 million tokens
TOKEN_PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("openai", "gpt-4o-mini"):              {"input": 0.15,  "output": 0.60},
    ("claude", "claude-sonnet-4-20250514"): {"input": 3.00,  "output": 15.00},
    ("gemini", "gemini-2.0-flash"):         {"input": 0.075, "output": 0.30},
    ("gemini", "gemini-2.5-flash"):         {"input": 0.15,  "output": 0.60},
}

# USD per 1,000 billable (non-cache) calls — India CPM
#
# ┌───────────────────────┬──────────────────────────────────────┬────────────┬─────────┬──────────┐
# │ op                    │ SKU                                  │ Tier       │ Free/mo │ CPM(USD) │
# ├───────────────────────┼──────────────────────────────────────┼────────────┼─────────┼──────────┤
# │ place_details_v1      │ V1 Find Place + Places Details       │ Pro        │ 35,000  │  5.10    │
# │ place_details_v2      │ V2 Text Search + Place Details Pro   │ Pro        │ 35,000  │  5.10    │
# │                       │ +FETCH_RATING → Enterprise (India)   │ Enterprise │  7,000  │  6.00    │
# │ nearby_or_text_search │ V1 text: Text Search (India)         │ Pro        │ 35,000  │  9.60    │
# │                       │ V1 nearby: Nearby Search (India)     │ Pro        │ 35,000  │  9.60    │
# │                       │ V2 text: Text Search Pro (India)     │ Pro        │ 35,000  │  9.60    │
# │                       │ V2 nearby: Nearby Search Pro (India) │ Pro        │ 35,000  │  9.60    │
# │                       │ V2 +FETCH_RATING → Enterprise        │ Enterprise │  7,000  │ 10.50    │
# │ directions            │ V1: Directions (India)               │ Essentials │ 70,000  │  1.50    │
# │ routes                │ V2: Compute Routes Ess. (India)      │ Essentials │ 70,000  │  1.50    │
# │ photo_url             │ V1: Places Photo (India)             │ Enterprise │  7,000  │  2.10    │
# │                       │ V2: Place Details Photos (India)     │ Enterprise │  7,000  │  2.10    │
# │ enrich_batch          │ (composite — no separate SKU)        │ —          │ —       │  0.00    │
# └───────────────────────┴──────────────────────────────────────┴────────────┴─────────┴──────────┘
MAPS_PRICING: dict[str, float] = {
    "place_details_v1":      5.10,  # Legacy Find Place + Places Details (Pro, 35K free)
    "place_details_v2":      5.10,  # New Text Search + Place Details Pro (35K free). +FETCH_RATING → Enterprise 6.00 (7K free)
    "nearby_or_text_search": 9.60,  # V1/V2 Pro (35K free). +FETCH_RATING → V2 Enterprise 10.50 (7K free)
    "directions":            1.50,  # V1 Directions Essentials (70K free)
    "routes":                1.50,  # V2 Compute Routes Essentials (70K free)
    "photo_url":             2.10,  # Places Photo Enterprise (7K free). Only billed when FETCH_PHOTOS=True
    "enrich_batch":          0.00,  # composite of find_place + place_details — don't double-count
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
