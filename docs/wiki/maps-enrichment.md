# Maps Enrichment

How the Maps service hydrates LLM-generated items with real place data
(place_id, lat/lng, address, rating, photos, types). Implemented in
`backend/app/services/google_maps/base.py:307`.

---

## Entry points

Two related methods on `BaseMapService`:

- **`enrich_items(items, *, user_id, trip_id) -> list[dict]`** — batch
  hydrator (`base.py:346`).
- **`enrich_items_with_summary(items, *, user_id, trip_id) -> (list[dict], EnrichmentSummary)`**
  — same plus a structured report on what failed (`base.py:390`).

`/llm/plan-trip` and `/brainstorm/extract` both call the `_with_summary`
variant.

---

## Input

A list of "brainstorm item" dicts produced by `llm_item_to_brainstorm()`
(`roammate_v1.py:52`). Each dict already has LLM fields filled and Maps
fields nulled:

```python
{
  "title": "Wat Pho Temple",
  "description": "Reclining Buddha and traditional massage",
  "category": "Religious & Spiritual",
  "time_category": "morning",
  "price_level": 0,
  "types": ["temple", "landmark"],
  # populated by enrichment:
  "place_id": None,
  "lat": None,
  "lng": None,
  "address": None,
  "photo_url": None,
  "rating": None,
}
```

Plus optional `user_id` / `trip_id` — only used for usage tracking
(`track_call`).

The item is treated as **idempotent**: if `place_id` is already set,
`enrich_item` returns it unchanged (`base.py:313`). A missing `title` is
also a no-op.

---

## Pipeline per item — `enrich_item` (`base.py:307`)

```
title ──► find_place(title)           # text query → place candidate
        ──► _extract_place_id(cand)   # pull id off the candidate
        ──► place_details(pid)        # full record
              └── _apply_details()    # merge canonical fields onto item
        (if place_details fails)
        ──► _apply_find_place_fallback(item, cand, pid)
```

`find_place`, `place_details`, `_apply_details`, `_extract_place_id` and
`_apply_find_place_fallback` are **abstract** — concrete impls live in
`google_maps/v1.py`, `v2.py`, `mock.py`, and `apple_maps/`. The base
class owns the orchestration; each version owns response parsing.

### Which calls actually hit Google?

`find_place` and `place_details` are the **only two methods in the
enrichment path that make outbound HTTP calls to Google**. Everything
else (cache, breaker, retry, telemetry, field mapping) is orchestration
around those two.

In the v2 impl (`google_maps/v2.py`):

- **`find_place(query)`** → `POST https://places.googleapis.com/v1/places:searchText`
  - Body: `{"textQuery": query}` (the item's `title`)
  - Headers: `X-Goog-Api-Key`, `X-Goog-FieldMask: _SEARCH_TEXT_FIELD_MASK`
  - Returns `data.places[0]` (or `None`)

- **`place_details(place_id)`** → `GET https://places.googleapis.com/v1/places/{place_id}`
  - Header: `X-Goog-FieldMask` built dynamically — you only pay for the
    fields you actually want (rating/photos are toggleable via
    `GOOGLE_MAPS_FETCH_RATING` / `GOOGLE_MAPS_FETCH_PHOTOS`).

So enriching one item costs **2 Places API requests** in the worst case
(find + details), or **1** if `place_details` fails and we fall back to
the leaner `find_place` payload via `_apply_find_place_fallback`.

### Cache / breaker / retry layers in front of those calls

A "real Google call" only happens on a cache miss + breaker-closed +
key-present path:

```
enrich_item
  └─ find_place
      ├─ gmap_cache.get_find_place(query)   ← hit? return cached candidate
      ├─ breaker.allow()                    ← open? return None
      ├─ HTTP POST searchText               ← the real call
      ├─ breaker.record_success / _failure
      ├─ gmap_cache.set_find_place
      └─ _track(...)                        ← telemetry → admin_costs
  └─ place_details
      ├─ gmap_cache.get_place_details(pid, field_mask)
      ├─ breaker.allow()
      ├─ HTTP GET places/{id}               ← the real call
      └─ same cache / breaker / track tail
```

`_request_with_retry` (`base.py:175`) handles exponential backoff for
429 / 5xx up to `MAX_RETRIES = 3`.

### Other Google calls that exist but aren't part of enrichment

For completeness, these are also real API calls but live **outside**
the enrich path:

- **`directions(waypoints)`** → Routes API (`base.py:529`) — travel-time
  computation on the live trip page.
- **`timezone_for(lat, lng)`** → Time Zone API (`base.py:439`) — called
  once after enrichment in `/llm/plan-trip` to infer the trip's IANA tz.
- **`nearby_search(query, lat, lng, ...)`** → Text Search or Nearby
  Search (`v2.py:341`) — used by the Concierge for "find me a coffee
  shop near here" intents, not by brainstorm enrichment.

### Mock mode

`MockMapService` (`google_maps/mock.py`) overrides `find_place` /
`place_details` / `_directions_api_call` to return deterministic stub
data — no network. That's what runs in tests and when
`GOOGLE_MAPS_API_KEY` is unset in mock mode.

### v2 field mapping — `google_maps/v2.py:288`

`_apply_details` merges:

- `place_id` ← `details.id`
- `lat`, `lng` ← `details.location.{latitude,longitude}`
- `address` ← `details.formattedAddress`
- `rating`, `price_level` (gated by `GOOGLE_MAPS_FETCH_RATING`)
- `photo_url` ← first photo, via `photo_url(name)` (gated by `GOOGLE_MAPS_FETCH_PHOTOS`)
- `types` ← first 5 Google types (only if LLM didn't already set tags)

---

## Pipeline for the batch — `enrich_items` (`base.py:346`)

1. Early return if `items` is empty.
2. **Missing API key (and not mock mode)** → returns items unchanged,
   tracks `no_api_key`. Does not error.
3. Stashes `user_id` / `trip_id` on `self` so `_track` can attach them
   to every call's telemetry.
4. Opens one `httpx.AsyncClient` per batch, runs all items through
   `asyncio.Semaphore(ENRICH_CONCURRENCY=5)` via
   `asyncio.gather(..., return_exceptions=False)`.
5. Emits one `enrich_batch` telemetry row with `batch_size`,
   `enriched_count`, `skipped_count`, `breaker_state`, total latency.

### Per-item error handling

Errors are swallowed inside `enrich_item` (`base.py:331-343`):

| Exception | `_last_failure_reason` |
|---|---|
| `HTTPStatusError` status 429 | `quota_exceeded` |
| Other `HTTPStatusError` | `upstream_error` |
| `NetworkError` / `TimeoutException` | `network_error` |
| Anything else | `upstream_error` |

The item is still returned — just without place fields.

---

## Pipeline for `_with_summary` (`base.py:390`)

Wraps `enrich_items` with two short-circuit guards and a summary builder:

1. Empty input → `EnrichmentSummary(status="full", total=0, enriched=0, skipped=0)`.
2. **No API key** (real mode) → returns items unchanged, `status="none"`,
   `reason="missing_api_key"`. **No HTTP calls.**
3. **Circuit breaker open** (`breaker.allow()` → False, real mode) →
   same shape, `reason="breaker_open"`. **No HTTP calls.**
4. Otherwise run `enrich_items`, then count successes by
   `r.get("place_id")`:
   - `enriched == total` → `status="full"`, `reason=None`
   - `0 < enriched < total` → `status="partial"`, `reason=_last_failure_reason`
   - `enriched == 0` → `status="none"`, `reason=_last_failure_reason`

The breaker (`google_maps/breaker.py`) is updated by the *Directions* /
*timezone* paths' explicit `record_success` / `record_failure` calls;
`enrich_item` itself does not record breaker outcomes (it only reads
via the `_with_summary` short-circuit).

---

## Output

**`enrich_items`** returns the same `list[dict]`, same length, same
order. Successfully-hydrated items gain the Maps fields in-place;
failures are returned untouched.

**`enrich_items_with_summary`** returns a tuple
`(list[dict], EnrichmentSummary)` where:

```python
class EnrichmentSummary(BaseModel):
    status: Literal["full", "partial", "none"]
    total: int
    enriched: int          # items where place_id ended up set
    skipped: int
    reason: Optional[Literal[
        "quota_exceeded", "missing_api_key", "breaker_open",
        "network_error", "upstream_error",
    ]] = None
```

The endpoint layer converts that into a nullable `EnrichmentStatus`
(only sent to the client when status ≠ `full`); the frontend renders it
as the amber "X of Y places couldn't be loaded" banner.

---

## Side effects worth knowing

- **No DB writes inside enrichment** — it's a pure transformation. The
  endpoint is responsible for persisting the returned dicts.
- **Cache** — `find_place` / `place_details` use the cache layer in
  `google_maps/cache.py` per version impl, so repeat enrichments of the
  same title are cheap.
- **Tracking** — every call funnels through `tracker.track_call`, which
  is what feeds `admin_costs.py` and the cost dashboards.
- **iOS** — when the request carries `X-Client-Platform: ios`, the
  endpoint dependency `_get_enrichment_service` swaps the Google
  service for the Apple Maps adapter; the abstract surface above is
  identical so the endpoint code doesn't branch.

---

## Key files

- `backend/app/services/google_maps/base.py` — `enrich_item`, `enrich_items`, `enrich_items_with_summary`, `EnrichmentSummary`
- `backend/app/services/google_maps/v1.py` — legacy API hooks
- `backend/app/services/google_maps/v2.py` — new Places API hooks (`_apply_details` shape)
- `backend/app/services/google_maps/mock.py` — mock-mode hooks
- `backend/app/services/google_maps/cache.py` — per-call cache layer
- `backend/app/services/google_maps/breaker.py` — circuit breaker
- `backend/app/services/google_maps/tracker.py` — usage telemetry
- `backend/app/services/apple_maps/` — Apple Maps adapter (iOS clients)
- `backend/app/schemas/enrichment.py` — wire-shape `EnrichmentStatus`

---

## Caveat

### Inputs

1. `query: str` (positional, required)

A free-text place query. In the enrichment path this is always the
item's title — whatever the LLM emitted in `LLMItem.t` (e.g. `"Wat Pho
Temple"`, `"Jay Fai street food"`, `"Chatuchak Weekend Market"`).

- No structured fields — no city, no lat/lng bias, no language hint.
  Just the title string.
- Empty / falsy query short-circuits to `None` (`v2.py:84`) before any
  cache or network work.
- Whatever the LLM wrote is sent verbatim. There's no normalisation,
  trimming, or city-append step before the call.

This is also the cache key — `gmap_cache.get_find_place(query)` hashes
on the raw query string, so `"wat pho"` and `"Wat Pho Temple"` are
separate cache entries.

### What `find_place` does not take

Notable absences vs. what Google's `places:searchText` API actually
supports:

- No `locationBias` / `locationRestriction` — the brainstorm pipeline
  doesn't yet pass city or lat/lng to bias results. That's why item
  titles need to be reasonably specific.
- No `languageCode` / `regionCode`.
- No `includedType` filter — even though the LLM has `category` and
  `types`, none of it is forwarded to Google.
- No `maxResultCount` — implementation always takes `places[0]`.
- No timeout override — uses the base class's `REQUEST_TIMEOUT_S = 10.0`.
