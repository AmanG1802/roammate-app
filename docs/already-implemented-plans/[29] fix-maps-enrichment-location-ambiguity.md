# Plan: Fix location-ambiguity in Maps enrichment

## Context

When the LLM emits a generic item title like "Commercial Street" for a Bengaluru trip, `find_place` returns the New York "Commercial Street" because the title is sent verbatim with no geographic context. The same happens across services (Google v2, v1, Apple Maps) — none of their `find_place` impls currently pass any biasing fields to the upstream API, even though all three SDKs support it (and our own `nearby_search` already uses it).

Two contributing facts:
1. **Cache key is the normalised query string only** (`backend/app/services/google_maps/cache.py:49`) — any biasing fix must extend the cache key, otherwise an early Bengaluru lookup poisons a later New York lookup (or vice versa).
2. The `Trip` model has **no destination fields** today (`backend/app/models/all_models.py:64-81`), so `/brainstorm/extract` (the in-trip re-enrich path) has nothing to bias from.

Goal: produce the right place for the right city by threading a structured `LocationContext` (lat/lng + radius + country code + language) from the call-sites into each provider's `find_place`, and emit the matching native bias fields per provider. Behaviour stays correct when context is absent (no bias → today's behaviour).

The intended outcome:
- `/llm/plan-trip` geocodes the destination once per request and enriches with bias.
- The preview carries the destination back to the client; `POST /trips/` persists it on the Trip row.
- `/brainstorm/extract` reads destination off the Trip and biases re-enrichment.
- Cache stays correct across trips.

---

## Approaches considered

### A. Structured `LocationContext` threaded through the enrich pipeline + provider-native bias (**recommended**)
Adds a `LocationContext` dataclass on the abstract surface, plumbs it from endpoint → `enrich_items` → `enrich_item` → `find_place`. Each provider translates it to its native fields (Google v2 `locationBias` + `regionCode` + `languageCode`; Google v1 `locationbias=circle:r@lat,lng` + `region` + `language`; Apple `searchLocation` + `searchRadius` + `lang`). Cache key extends with a bias fingerprint. **Why pick this:** soft `locationBias` (ranking signal) combined with `regionCode` (country gate) catches both intra-country ("California vs New York") and cross-country ("Bengaluru vs NYC") collisions without hard-filtering legitimate day-trip outliers. Backwards-compatible: no `LocationContext` → today's behaviour.

### B. Query-string suffixing (band-aid alternative)
In `enrich_item`, append `", {city}, {country}"` to the title before calling `find_place`. No new schema, no new params, no provider-specific work, and the cache key naturally diverges because the query string is the cache key. **Trade-offs:** still purely text-ranking (no structured filter, so "Commercial Street, Bengaluru, India" can still rank a NYC match higher if Google's index is bad); risks double-suffixing when the LLM already qualified ("Wat Pho Temple, Bangkok"); doesn't fix the underlying gap in `find_place`. Useful as a 30-minute hotfix while A ships; not the long-term answer.

**Recommended: Approach A.** If a fast pre-deploy band-aid is needed, ship B's title-suffix line in `enrich_item` as a stop-gap and remove it after A lands.

---

## Source of destination (city, country, centroid)

User's answers determined this:

- **City + country code** preferred from the **LLM** (`LLMPlanResponse.destination_city`, `country_code`), with `pre_extract` (`backend/app/services/llm/pre_processor.py:132`) as the fallback. Rationale: `_CITY_COUNTRY` is a hardcoded ~50-city table — fine for common destinations, brittle for long-tail ("Hampi", "Banff"), multi-word ("San Francisco"), and ambiguous names ("Florence" — Italy vs SC). The LLM has world knowledge + full prompt context, so it disambiguates better. Pre-extract is a safety net.
- **Centroid lat/lng**: one-shot geocode of `"{city}, {country}"` via the same provider's `searchText`/`findplace`/Apple `search` (i.e., the same `find_place` we already have, with `regionCode` set). Cached aggressively per `(city, country_code)`.
- **Trip row** persists `destination_city`, `country_code`, `destination_lat`, `destination_lng` (all nullable) so `/brainstorm/extract` can reuse them without re-geocoding.

---

## File-by-file changes (Approach A)

### 1. Schema & model

**`backend/app/models/all_models.py`** — extend `Trip`:
- `destination_city: Mapped[Optional[str]]`
- `country_code: Mapped[Optional[str]]` (length 2, ISO-3166-1 alpha-2)
- `destination_lat: Mapped[Optional[float]]`
- `destination_lng: Mapped[Optional[float]]`

**Alembic migration** under `backend/alembic/versions/` — nullable columns, no backfill needed.

**`backend/app/schemas/llm.py`** — extend `LLMPlanResponse` (`:52`):
- `destination_city: Optional[str]`
- `country_code: Optional[str]` (validate `len == 2` if provided)

**`backend/app/schemas/trip.py`** — extend `TripCreate` to accept the four destination fields (all optional).

**`backend/app/schemas/brainstorm.py`** — extend `PlanTripResponse` with the four destination fields so the preview can hand them to the create-trip POST.

### 2. Prompt update

**`backend/app/services/llm/services/v1/prompts/plan_trip_v1.txt`** — extend the schema instructions to require:
- `destination_city`: human-readable city
- `country_code`: ISO-3166-1 alpha-2 (e.g., `IN`, `US`, `ES`)

`pre_processor._CITY_COUNTRY` (`pre_processor.py:21`) already maps name→country; extend the values to include alpha-2 codes so the fallback returns the same shape.

### 3. Abstract surface — `LocationContext`

**`backend/app/services/google_maps/base.py`** — new dataclass + signature changes:

```python
@dataclass
class LocationContext:
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_m: int = 50_000      # soft bias; ~city-scale
    country_code: Optional[str] = None  # ISO-3166-1 alpha-2
    language_code: Optional[str] = None # ISO 639-1

    def fingerprint(self) -> Optional[str]:
        """Cache-key-safe summary. Returns None when there's no real bias."""
        ...
```

Update abstract signatures (also propagates to v1, v2, mock, apple):
- `find_place(query, *, client=None, location: Optional[LocationContext] = None)`
- `enrich_item(item, *, client=None, location: Optional[LocationContext] = None)`
- `enrich_items(items, *, user_id=None, trip_id=None, location: Optional[LocationContext] = None)`
- `enrich_items_with_summary(...)` likewise

`enrich_items` passes `location` into each `_runner` → `enrich_item` → `find_place`. The orchestration code in `enrich_item` (`base.py:307`) gets one line touched.

### 4. Cache key extension

**`backend/app/services/google_maps/cache.py`** — `get_find_place`/`set_find_place` accept an optional `bias_fp: Optional[str]` and include it in the key tuple. `_normalize_query` stays as-is. A `None` fingerprint preserves today's keying for the no-bias path, so existing entries aren't invalidated.

Fingerprint format: `f"{country_code or '-'}|{lat:.2f},{lng:.2f}|{radius_m//1000}"` (rounding to ~1 km).

### 5. Per-provider implementations

**`backend/app/services/google_maps/v2.py` (`:78` and `:178`)** — `find_place`:
- When `location` is set, add to `json_body`:
  - `locationBias = {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": radius_m}}` (only if lat+lng)
  - `regionCode = country_code` (if set)
  - `languageCode = language_code` (if set)
- Pattern is already proven by `nearby_search` at `v2.py:380`.
- Pass `location.fingerprint()` to `gmap_cache.get_find_place` / `set_find_place`.

**`backend/app/services/google_maps/v1.py` (`:60`)** — `find_place`:
- Legacy Find Place from Text supports `locationbias=circle:{radius}@{lat},{lng}` and `language`, `region` params — add to `params` dict when `location` is set.
- Same cache fingerprint plumbing.
- `_apply_find_place_fallback` (`v1.py:279`) unchanged.

**`backend/app/services/apple_maps/service.py` (`:56`)** — `find_place`:
- Add `searchLocation = f"{lat},{lng}"` and `searchRadius = str(radius_m)` to params when `location` has coords (pattern already used in `nearby_search` at `:192-193`).
- Add `lang = language_code` if set.
- Apple has no direct `country_code` filter for the Search endpoint; the centroid + radius is the disambiguator. Document this limitation in the docstring.
- Same cache fingerprint plumbing.

**`backend/app/services/google_maps/mock.py`** — accept and ignore the new param; update signatures only.

### 6. Geocoder helper

**New file: `backend/app/services/google_maps/geocoding.py`** — small async helper:

```python
async def geocode_city(
    svc: BaseMapService,
    city: str,
    country_code: Optional[str],
    *,
    user_id: Optional[int] = None,
) -> Optional[LocationContext]:
    """One-shot geocode using the provider's own find_place.
    Returns a populated LocationContext or None on failure.
    Cached per (city, country_code) via gmap_cache."""
```

Implementation: call `svc.find_place(f"{city}, {country_code}", location=LocationContext(country_code=country_code))`, extract lat/lng via the provider's `_apply_find_place_fallback`-equivalent path, build `LocationContext(lat, lng, radius_m=50000, country_code=country_code)`. This reuses every layer we already have (cache, breaker, telemetry).

Add `gmap_cache.get_city_centroid` / `set_city_centroid` with 30-day TTL to avoid burning a request on every plan-trip for the same city.

### 7. Endpoint wiring

**`backend/app/api/endpoints/llm.py` — `/llm/plan-trip` (`:33`)**:
1. After `client.plan_trip(...)`, pull `destination_city` + `country_code` from `result`; fall back to `pre_extract(body.prompt)` for either field if the LLM didn't return one.
2. `loc = await geocode_city(maps_svc, city, country_code, user_id=current_user.id)` (may be `None` if geocode fails or city was unknown).
3. Pass `location=loc` into `maps_svc.enrich_items_with_summary(...)`.
4. Add the four destination fields to `PlanTripResponse`.

**`backend/app/api/endpoints/trips.py`** (the POST handler) — accept the four optional fields in `TripCreate`, persist on the `Trip` row.

**`backend/app/api/endpoints/brainstorm.py` — `/brainstorm/extract` (`:251`)**:
1. Fetch the `Trip` row (already happens for `promote`; add it here).
2. If `trip.destination_lat` and `trip.destination_lng` are set, build a `LocationContext` from the row.
3. Pass `location=ctx` to `maps_svc.enrich_items_with_summary(...)`.

### 8. Frontend wiring

**`frontend/components/dashboard/DashboardTripPlanner.tsx` (`:112`)** — extend the `POST /trips/` body to include `destination_city`, `country_code`, `destination_lat`, `destination_lng` from `preview` (already returned by `/llm/plan-trip` after step 7).

### 9. Tests

Add to `backend/tests/services/google_maps/`:
- `LocationContext` propagation: assert v2 emits `locationBias`/`regionCode`/`languageCode` in JSON body when set, omits when not.
- v1 emits `locationbias=circle:...`/`region`/`language` query params when set.
- Apple Maps emits `searchLocation`/`searchRadius`/`lang` when set.
- Mock no-ops with the new param.
- **Cache isolation**: enriching `"Commercial Street"` under Bengaluru ctx and then NYC ctx returns the right place each time (one cached entry per fingerprint).
- **Backwards compat**: enrich without `location` produces identical output and uses the legacy cache key.
- **Geocode caching**: two consecutive `/llm/plan-trip` calls for Bengaluru issue exactly one geocode HTTP request.

End-to-end (`backend/tests/api/`):
- `/llm/plan-trip` for "5 days in Bengaluru" enriches a `Commercial Street` item to the Bengaluru place (mock service returns the closest-to-centroid candidate).
- After create-trip, `/brainstorm/extract` for a chat-added `"Commercial Street"` also resolves to Bengaluru via Trip-stored centroid.
- Fallback: when LLM omits `destination_city`, pre_extract supplies it.

---

## Verification (manual, end-to-end)

1. Run backend in real mode with `GOOGLE_MAPS_API_KEY` set, `LLM_ENABLED=true`.
2. From the dashboard, run **Plan Trip**: `"3-day Bengaluru itinerary with food and markets"`. Confirm:
   - Network tab: the `POST /api/llm/plan-trip` response includes `destination_city: "Bengaluru"`, `country_code: "IN"`, destination lat/lng populated.
   - At least one item titled "Commercial Street" — verify it resolves to the Bengaluru location (check the address / lat ≈ 12.98, lng ≈ 77.61).
3. **Create Trip and Take Me There** — confirm `Trip` row in DB has destination fields filled.
4. In the brainstorm chat, prompt: `"add Commercial Street to my list"`. After Extract: confirm the new bin item points to Bengaluru, not NYC.
5. Repeat steps 1-4 for `"3 days in New York"` with `"Commercial Street"` and confirm it resolves to NYC.
6. iOS client: send the same flow with `X-Client-Platform: ios` header; confirm Apple Maps adapter is hit (admin cost dashboard should show Apple calls, not Google) and disambiguates correctly.
7. v1 path: temporarily flip the service config to v1, repeat the Bengaluru check.
8. Cache sanity: hit the same prompt twice; second call should be all cache hits in the tracker (`status=cache_hit`).

---

## Critical files (touched / read)

- `backend/app/services/google_maps/base.py` — `LocationContext`, signature changes, enrich plumbing
- `backend/app/services/google_maps/v2.py` — `find_place` bias fields
- `backend/app/services/google_maps/v1.py` — `find_place` bias params
- `backend/app/services/google_maps/mock.py` — signature only
- `backend/app/services/google_maps/cache.py` — fingerprint in cache key, new city-centroid cache
- `backend/app/services/google_maps/geocoding.py` — **new** helper
- `backend/app/services/apple_maps/service.py` — `find_place` searchLocation/searchRadius/lang
- `backend/app/services/llm/pre_processor.py` — extend `_CITY_COUNTRY` to map name → (country, alpha-2)
- `backend/app/services/llm/services/v1/prompts/plan_trip_v1.txt` — request `destination_city` + `country_code`
- `backend/app/services/llm/services/v1/roammate_v1.py:228` — surface new fields from `LLMPlanResponse` in the return dict
- `backend/app/schemas/llm.py:52` — extend `LLMPlanResponse`
- `backend/app/schemas/brainstorm.py` — extend `PlanTripResponse`
- `backend/app/schemas/trip.py` — extend `TripCreate`
- `backend/app/models/all_models.py` — `Trip` columns
- `backend/alembic/versions/<new>.py` — migration
- `backend/app/api/endpoints/llm.py:33` — geocode + thread `location`
- `backend/app/api/endpoints/trips.py` — persist destination fields
- `backend/app/api/endpoints/brainstorm.py:251` — read Trip → `LocationContext`
- `frontend/components/dashboard/DashboardTripPlanner.tsx:112` — pass destination fields in `POST /trips/`

## Things explicitly out of scope

- `nearby_search` (already biased correctly).
- Concierge intents — they get lat/lng from the active event/trip context, not from titles.
- A user-facing "trip destination" editor — the data is captured during plan-trip; manual edit can wait.
- v1 endpoint switch to Text Search — sticking with Find Place from Text + `locationbias` keeps the diff minimal and the cost model unchanged.
- Radius tuning per destination size (Tokyo metro vs. a small town). 50 km is a safe default; revisit only if we see misses.
