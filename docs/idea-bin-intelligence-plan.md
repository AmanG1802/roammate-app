# Idea Bin Intelligence Upgrade — Future Plan

## Current State

`backend/app/services/idea_bin.py` (`IdeaBinService.ingest_from_text`) is the text ingestion path for the Idea Bin. It is called from `POST /trips/{id}/ingest` in `trips.py`.

Today it does:

1. Split user text on commas / newlines into individual lines.
2. Per line: extract a time hint via regex (e.g., "at 2pm").
3. Per line: call `google_maps_service.find_place(clean_line)` to resolve place_id + lat/lng.
4. Create an `IdeaBinItem` row with title + optional place data.

There is **zero intelligence** — no category inference, no description, no time_category, no duration estimation, no dedup against existing items. If a user pastes a blog paragraph, each raw line becomes a separate item. Messy input produces messy results.

## Why Upgrade

This is the 1A.1 use case from the Phase 1A plan:

> "Users paste messy, heterogeneous input — a travel-blog paragraph, a WhatsApp message, a list, a single place name — and get back a clean, enriched, deduplicated set of Idea Bin items."

The full infrastructure already exists:

- `RoammateServiceV1.extract_items()` — LLM-powered extraction with structured output (`LLMExtractResponse` schema), returning items with title, description, category, time_category, price_level, tags.
- `pre_processor.py` — zero-LLM extraction of city, dates, budget, vibes from free text.
- `place_enricher.py` — Google Places hydration (place_id, lat, lng, address, rating, hours, phone, website, photo_url).
- `dedup.py` — exact place_id + fuzzy title dedup against existing items.
- `llm_item_to_brainstorm()` — field mapping from abbreviated LLM output to BrainstormBinItem-compatible dicts.

## Proposed Approach

Route the ingestion text through the LLM pipeline instead of dumb line splitting.

### When LLM_ENABLED = True

```
User text
  → pre_extract() for city/date/budget context
  → Build messages with brainstorm_extract_v1.txt system prompt + user text as a single user message
  → model.complete(schema=LLMExtractResponse, temperature=0.3)
  → Parse LLMItems → llm_item_to_brainstorm() field mapping
  → enrich_items() for Google Places hydration
  → deduplicate() against existing trip IdeaBinItems
  → Create IdeaBinItem rows
```

### When LLM_ENABLED = False

Fall back to the current comma-split + Google Places approach so the existing test suite works without API keys.

### Endpoint

Keep `POST /{trip_id}/ingest` as-is — it's a distinct UX surface from the brainstorm chat + extract flow. The user pastes text directly into the Idea Bin (no chat conversation), so the endpoint stays but calls smarter internals.

### Implementation Steps

1. Update `IdeaBinService.ingest_from_text()` to check `settings.LLM_ENABLED`.
2. If enabled: build a one-message history `[{"role": "user", "content": text}]` and call `get_brainstorm_client().extract_items(history)`.
3. Run `enrich_items()` + `deduplicate()` on the result (same as the brainstorm extract endpoint).
4. Map results to `IdeaBinItem` rows (the extract pipeline returns BrainstormBinItem-compatible dicts, which share the same fields).
5. If disabled: keep the current line-split + Google Places fallback.
6. Update tests to mock the LLM client path.

### What This Unlocks

- Blog paragraphs, WhatsApp messages, mixed-format lists all produce clean structured items.
- Each item gets a category, description, time_category, price_level, and tags — not just a title.
- Dedup prevents duplicate items when the user pastes overlapping text.
- Google Places enrichment fills in real coordinates, photos, and hours.

## Status

Deferred — to be picked up as a separate task after the current LLM pipeline work stabilises.
