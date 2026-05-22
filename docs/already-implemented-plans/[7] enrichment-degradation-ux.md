# Enrichment Degradation — UX Gap

## Problem

When Google Maps enrichment fails (invalid key, quota exhausted, circuit breaker open, network error), the backend silently returns unenriched items. The user receives items with:

- No photo (empty image / placeholder)
- No lat/lng (item can't appear on the map)
- No address (just a bare title like "Wat Pho")
- No rating / price_level (missing social proof)

There is **no feedback** to the user explaining why data is missing. They may assume the LLM gave bad suggestions or the app is broken.

## Affected Flows

| Flow | Enrichment? | Impact |
|------|-------------|--------|
| **Plan Trip** (`POST /plan-trip`) | Yes — inline via `enrich_items` | **High** — first impression flow; 10-15 bare items looks broken |
| **Extract** (`POST /brainstorm/extract`) | Yes — inline via `enrich_items` | **Medium** — brainstorm bin, user is iterating, but still jarring |
| **Chat** (`POST /brainstorm/chat`) | No | None |

## Current Backend Behaviour (correct, but invisible)

- `enrich_item` catches all exceptions and returns the item unenriched (`base.py:284`)
- `enrich_items` logs `enriched_count` vs `skipped_count` via the tracker — but this data never reaches the frontend
- The circuit breaker opens after repeated failures and short-circuits subsequent calls
- The factory falls back to `MockMapService` when `GOOGLE_MAPS_API_KEY` is missing

Engineering-wise this is the right approach (never crash the endpoint). The gap is in the **feedback loop to the user**.

## Proposed Improvements

### Lightweight (no architecture change)

- Add an `enrichment_status` field to `BrainstormExtractResponse` and `PlanTripResponse`:
  - `"full"` — all items enriched
  - `"partial"` — some items enriched, some failed
  - `"none"` — enrichment entirely unavailable
- Frontend shows a subtle banner: *"Some places couldn't be loaded. Try refreshing later."*
- Use a distinct card style for unenriched items (text-only, search icon instead of broken image)

### Medium

- Bubble up `enriched_count` / `skipped_count` from the tracker into the API response
- Frontend offers a per-item "Retry enrichment" button that calls a dedicated endpoint
- Track which items failed and why (quota vs key vs network) for better messaging

### Heavier (future scope)

- Queue failed enrichments for async retry (Redis job) and push-notify the user on completion
- Pre-validate LLM place names against a lightweight gazetteer before hitting Google
- Batch-retry on circuit breaker recovery

## Related Files

- `backend/app/services/google_maps/base.py` — `enrich_item`, `enrich_items`
- `backend/app/services/google_maps/tracker.py` — already logs `enriched_count` / `skipped_count`
- `backend/app/api/endpoints/brainstorm.py` — extract endpoint
- `backend/app/api/endpoints/llm.py` — plan_trip endpoint
- `backend/app/schemas/brainstorm.py` — response schemas to extend
