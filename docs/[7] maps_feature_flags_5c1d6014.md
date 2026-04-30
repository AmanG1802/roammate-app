---
name: Maps Feature Flags
overview: Add two backend feature flags (GOOGLE_MAPS_FETCH_PHOTOS and GOOGLE_MAPS_FETCH_RATING) that control whether Place Photos and rating/price_level fields are fetched during enrichment. Dynamically adjust the Place Details field masks to match, downgrading the billing tier when these fields are off. Expose these flags to the frontend via a new /api/config endpoint and conditionally hide photo/rating UI elements in BrainstormBin, IdeaBin, and Timeline cards.
todos:
  - id: config
    content: Add GOOGLE_MAPS_FETCH_PHOTOS and GOOGLE_MAPS_FETCH_RATING to config.py, .env.example, docker-compose.yml (backend + frontend env vars)
    status: completed
  - id: v1-dynamic-fields
    content: Make V1 _DETAIL_FIELDS dynamic based on flags; gate _apply_details for rating/price_level/photo_url
    status: completed
  - id: v2-dynamic-fields
    content: Make V2 _PLACE_DETAILS_FIELD_MASK dynamic based on flags; gate _apply_details for rating/price_level/photo_url
    status: completed
  - id: mock-gating
    content: Gate MockMapService._apply_details to skip photo_url/rating/price_level when flags are off
    status: completed
  - id: frontend-brainstorm
    content: Gate photo and rating rendering in BrainstormBin.tsx based on NEXT_PUBLIC env vars
    status: completed
  - id: frontend-ideabin
    content: Gate photo and rating rendering in IdeaBin.tsx based on NEXT_PUBLIC env vars
    status: completed
  - id: frontend-timeline
    content: Gate photo and rating rendering in Timeline.tsx based on NEXT_PUBLIC env vars
    status: completed
  - id: tests
    content: "Add tests for flag-off scenarios: field masks exclude photos/rating, _apply_details skips them"
    status: completed
isProject: false
---

# Maps Enrichment Feature Flags

## Motivation

- **Place Photos** (Enterprise SKU): only 7,000 free/month, $2.10/1K after. Disabling saves the most constrained budget item.
- **rating + price_level** (Atmosphere/Pro SKU): bumps Place Details from 70K free/month (Essentials) to 35K free/month (Pro). Disabling doubles the free cap.

Two new boolean flags let us flip these on/off without code changes, instantly adjusting both the API cost profile and the UI rendering.

---

## New Configuration

Add to [backend/app/core/config.py](backend/app/core/config.py), [.env.example](.env.example), and [docker-compose.yml](docker-compose.yml):

```python
GOOGLE_MAPS_FETCH_PHOTOS: bool = True
GOOGLE_MAPS_FETCH_RATING: bool = True
```

Also expose as frontend env vars:

```
NEXT_PUBLIC_GOOGLE_MAPS_FETCH_PHOTOS=true
NEXT_PUBLIC_GOOGLE_MAPS_FETCH_RATING=true
```

---

## Backend Changes

### 1. Dynamic field masks in V1 and V2

Both [v1.py](backend/app/services/google_maps/v1.py) and [v2.py](backend/app/services/google_maps/v2.py) currently use static `_DETAIL_FIELDS` / `_PLACE_DETAILS_FIELD_MASK` constants. Change these to methods or properties on `BaseMapService` that read from settings at call time:

**V1** (`_DETAIL_FIELDS`):
- Base: `place_id,name,geometry,formatted_address,types`
- If `FETCH_RATING`: append `rating,price_level`
- If `FETCH_PHOTOS`: append `photos`

**V2** (`_PLACE_DETAILS_FIELD_MASK`):
- Base: `id,displayName,formattedAddress,location,types`
- If `FETCH_RATING`: append `rating,priceLevel`
- If `FETCH_PHOTOS`: append `photos`

This directly controls the billing tier Google assigns to the request.

### 2. Conditional `_apply_details` in V1 and V2

In both [v1.py](backend/app/services/google_maps/v1.py) and [v2.py](backend/app/services/google_maps/v2.py), the `_apply_details` method must skip setting `rating`, `price_level`, and `photo_url` when the corresponding flag is off. Even if the API returns these fields (e.g., cached or future re-enable), the flag controls whether they propagate to the item dict.

### 3. Conditional `photo_url` call

In `_apply_details`, the `self.photo_url(...)` call (which builds the URL that triggers a Photos API billing event when the browser fetches it) must be gated on `GOOGLE_MAPS_FETCH_PHOTOS`. When off, `photo_url` is never set on the item, so the `<img>` tag never renders, and no Photo API call fires.

### 4. Mock service

[mock.py](backend/app/services/google_maps/mock.py) should also respect these flags in its `_apply_details` so dev/CI behavior mirrors production. When `FETCH_PHOTOS=false`, mock should not set `photo_url`; when `FETCH_RATING=false`, mock should not set `rating`/`price_level`.

### 5. Cache field-signature isolation

The cache in [cache.py](backend/app/services/google_maps/cache.py) keys `place_details` on `(place_id, fields_sig)`. Since the field mask now varies based on the flags, the cache key will naturally isolate entries. If you flip a flag mid-session, old cached entries (with the old field set) won't conflict with new ones. No change needed in cache.py itself -- just ensure the field mask string passed to `set_place_details` / `get_place_details` reflects the current flag state.

---

## Frontend Changes

### 1. Read feature flags from env vars

The three UI components need access to the flags. Use `NEXT_PUBLIC_GOOGLE_MAPS_FETCH_PHOTOS` and `NEXT_PUBLIC_GOOGLE_MAPS_FETCH_RATING` env vars (same pattern as the existing `NEXT_PUBLIC_GOOGLE_MAPS_MOCK`).

### 2. BrainstormBin ([frontend/components/trip/BrainstormBin.tsx](frontend/components/trip/BrainstormBin.tsx))

- **Card (compact view, ~line 227)**: The `rating` badge (`<Star>` icon + rating value) is conditionally rendered with `{item.rating != null && ...}`. Add an outer guard: `{FETCH_RATING && item.rating != null && ...}`.
- **Tooltip/detail popover (~line 343-358)**: The `photo_url` image block is conditionally rendered with `{item.photo_url && ...}`. Add outer guard: `{FETCH_PHOTOS && item.photo_url && ...}`. Same for the rating badge at ~line 355.
- **"No details" fallback (~line 376)**: Adjust the condition `{!item.photo_url && !item.description && !item.address && ...}` to also account for the flags (e.g., treat `photo_url` as absent when `FETCH_PHOTOS` is off).

### 3. IdeaBin ([frontend/components/trip/IdeaBin.tsx](frontend/components/trip/IdeaBin.tsx))

- **Card (~line 315)**: Guard the rating badge with `FETCH_RATING`.
- **Popover (~line 431-442)**: Guard `photo_url` image with `FETCH_PHOTOS`, and rating badge with `FETCH_RATING`.
- **"No details" fallback (~line 458)**: Adjust the empty-state condition.

### 4. Timeline ([frontend/components/trip/Timeline.tsx](frontend/components/trip/Timeline.tsx))

- **`hasDetails` check (~line 283)**: Remove `event.photo_url` and `event.rating` from the expression when the respective flags are off, so the tooltip expand arrow doesn't appear for items that only had photo/rating data.
- **Tooltip body (~line 405-416)**: Guard the photo image with `FETCH_PHOTOS`, and the rating badge with `FETCH_RATING`.

---

## Billing Impact Summary

| Flags | Place Details SKU | Free Cap | Photos SKU | Photos Free |
|-------|-------------------|----------|------------|-------------|
| Both ON (default) | Pro (35K) | 35,000/mo | Enterprise (7K) | 7,000/mo |
| RATING OFF | Essentials (70K) | 70,000/mo | Enterprise (7K) | 7,000/mo |
| PHOTOS OFF | Pro (35K) | 35,000/mo | None (0) | N/A |
| Both OFF | Essentials (70K) | 70,000/mo | None (0) | N/A |

---

## Files to Modify

### Backend
- [backend/app/core/config.py](backend/app/core/config.py) -- add 2 settings
- [backend/app/services/google_maps/v1.py](backend/app/services/google_maps/v1.py) -- dynamic field string, conditional _apply_details
- [backend/app/services/google_maps/v2.py](backend/app/services/google_maps/v2.py) -- dynamic field mask, conditional _apply_details
- [backend/app/services/google_maps/mock.py](backend/app/services/google_maps/mock.py) -- conditional _apply_details
- [.env.example](.env.example) -- document new vars
- [docker-compose.yml](docker-compose.yml) -- pass through to backend + frontend

### Frontend
- [frontend/components/trip/BrainstormBin.tsx](frontend/components/trip/BrainstormBin.tsx) -- gate photo + rating rendering
- [frontend/components/trip/IdeaBin.tsx](frontend/components/trip/IdeaBin.tsx) -- gate photo + rating rendering
- [frontend/components/trip/Timeline.tsx](frontend/components/trip/Timeline.tsx) -- gate photo + rating rendering

### Tests
- [backend/tests/services/test_google_maps_service.py](backend/tests/services/test_google_maps_service.py) -- add tests for flag=off scenarios (field mask excludes photos/rating, _apply_details skips them)
