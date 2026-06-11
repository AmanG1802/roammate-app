# [52] Apple Maps Full Integration — Platform-Native Maps Routing

## Context

Roammate runs on two surfaces sharing one backend: **iOS (SwiftUI)** and **Web (Next.js)**.
A user can log into either platform for the same trip, so all *stored* map data must be
platform-agnostic. The goal of this work:

- **iOS requests use Apple Maps service only** — no Google Maps calls on the iOS path.
- **Web requests use Google Maps service only** — no Apple Maps calls on the web path.
- The data these services fill (coordinates, route polylines) must render on **both**
  platforms regardless of which service produced it.
- The **Refresh Route** button must invoke the platform's own map service.

Three concrete defects/gaps motivated this:

1. **Auth-gate bug (already fixed in working tree).** `BaseMapService` gated enrichment on
   `bool(self.api_key)`. `AppleMapsService` uses JWT (no API key), so iOS enrichment
   silently returned unenriched. Fixed via `_has_valid_auth()` hook
   (`base.py:201-205,405,454`; Apple overrides → `True`). **No further action.**
2. **Server-side travel-times always use Google.** `find-nearby`, `whats-next`, and Smart
   Ripple compute travel times with Google `directions()` even on iOS.
3. **`place_id` is provider-specific and leaks across platforms** (see reference below).

---

## Decisions (locked with product owner)

| # | Decision | Choice |
|---|----------|--------|
| 1 | **iOS itinerary route render** | **Keep on-device MKDirections.** iOS already computes the multi-stop route via `MKDirections` (= Apple Maps), encodes to a Google-format polyline, and POSTs to `/route/save` (pure storage). Zero Server-API quota, multi-stop native. Web stays Google server-side via `/maps/route`. The stored `encoded_polyline` renders on both platforms. **No backend Apple `/v1/directions` implementation.** |
| 2 | **iOS travel-time ETAs** (find-nearby, whats-next) | **Apple `/v1/etas` (batched).** One call returns ETAs for all find-nearby results; one call for whats-next. Cheapest quota use, no geometry (not needed for an ETA). Web unchanged (Google directions). |
| 3 | **Smart Ripple travel-times** | **Apple etas on the iOS path.** Smart Ripple always runs in an HTTP request context (the old "Celery, no header" premise was wrong), so `x-client-platform` *can* be threaded through `/shift` and the concierge executor. iOS-triggered ripples use Apple etas; web uses Google. |
| 4 | **`place_id` strategy** | **Always use lat/lng; `place_id` is display/dedup-only.** Routing and re-enrichment never interpret `place_id`. lat/lng is always present post-enrichment and is already what rendering uses, so this is fully provider-agnostic and removes all cross-provider breakage. |
| 5 | **Photos** | **Accept Apple = no photos.** No Apple API (Server or on-device MapKit) exposes a renderable place-photo URL (see reference). iOS-enriched items have no photo; web-enriched (Google) items show photos on both platforms. UI falls back to existing placeholder on empty `photo_url`. No cross-provider calls. |
| 6 | **"Already enriched" skip key** | **Skip when lat/lng present.** Change the idempotency gate from "has `place_id`" to "has lat/lng," so an item is enriched exactly once by whichever provider sees it first. |

---

## Reference — where `place_id` is used (audit, June 2026)

Kept here for future maintainers. `place_id` is interpreted in only three places; everything
else is pass-through storage. **Map rendering (pins + polylines) uses lat/lng only on both
iOS (`PlanMapPage.swift`) and web (`GoogleMap.tsx`) — never `place_id`.**

**A. Enrichment idempotency**
- `services/google_maps/base.py:362` — `enrich_item()` returns early if `place_id` set.
- `api/endpoints/maps.py:407-412` — re-enrich clears `place_id`, checks it for success.

**B. Routing / directions identity ⚠️ (the cross-provider break)**
- `base.py:106-117` — `RoutePoint.identifier()` / `is_valid()` prefer `place_id` over lat/lng.
- `google_maps/v1.py:392-393` — Google v1 sends `origin=place_id:{id}` when present (v2 similar).
- `services/smart_ripple.py:207-208` — `_event_to_route_point()` uses `place_id` **and drops
  lat/lng** when present. Worst case: an Apple MUID sent to Google → rejected.
- `google_maps/cache.py:5-6,63-64` — directions/place_details cache keyed on `place_id`/coords.

**C. Deduplication**
- `api/endpoints/brainstorm.py:327-338` — fuzzy dedup on `place_id` + Levenshtein(title).
- `api/endpoints/concierge.py:348` — `enriched_count` metric counts `place_id` presence.

**D. Pure pass-through (no provider logic)** — `services/idea_bin.py:30-36`,
`services/concierge_executor.py:278,335`, `api/endpoints/groups.py:565`,
`concierge.py:69,312-333`.

Decision 4 neutralizes **B** (stop populating `RoutePoint.place_id`; use lat/lng).
Decision 6 fixes **A.idempotency**. **C** stays as-is: dedup is already title-fuzzy, so
provider-mismatched `place_id`s simply don't match and the title match still catches dupes.

---

## Reference — Apple Maps photo limitation (audit, June 2026)

**No Apple API returns a renderable place-photo URL.**
- **Server API** (`maps-api.apple.com`, the only Apple API our backend can call): the Place
  object (`/v1/place/:id`, `/v1/search`) has **no photo field** — only name, coordinate,
  structuredAddress/formattedAddressLines, country, poiCategory, alternate IDs. Also no
  rating, price level, or hours. Hence `AppleMapsService.photo_url()` returns `""`
  (`apple_maps/service.py:148-149`) — genuine absence, not a stub.
- **On-device MapKit**: `MKMapItem`/Place Cards render photos only inside Apple's own UI; not
  exposed as fetchable URLs. `MKLookAroundScene` is street-level panorama, not place photos.

Therefore the **only** photo source in the stack is Google's photo endpoint (a normal HTTPS
URL with embedded key that renders on web and iOS). Per Decision 5, iOS-origin items stay
photo-less.

---

## Apple Maps Server API — relevant endpoints

Base `https://maps-api.apple.com`. Auth: `Authorization: Bearer <JWT>` (ES256, `.p8` key,
via `AppleMapsTokenProvider`). Shared quota: **25,000 calls/day per team**.

| Endpoint | Use here |
|---|---|
| `GET /v1/search` | `nearby_search` (already implemented) |
| `GET /v1/place/:id` | `place_details` (already implemented) |
| **`GET /v1/etas`** | **NEW — travel time + distance only, multi-destination** |
| `GET /v1/directions` | **Not used** (Decision 1: iOS routes on-device) |

`/v1/etas` request: `?origin=lat,lng&destinations=lat,lng|lat,lng|...&transportType=Automobile`
(up to **10 destinations** per call — chunk if more).
Response: `{ etas: [ { destination, distanceMeters, expectedTravelTimeSeconds }, ... ] }`.

---

## Implementation

### 1. Shared platform selector (de-dupe 3 existing helpers)

Today `_get_enrichment_service()` is copy-pasted in `endpoints/maps.py:54`,
`endpoints/brainstorm.py:259`, `endpoints/llm.py:24`. Add one shared helper and have all
three (plus the new call-sites) delegate to it.

**New file: `backend/app/services/maps_selector.py`**
```python
def select_map_service(x_client_platform: Optional[str]) -> BaseMapService:
    """Apple Maps for iOS clients when enabled, else Google."""
    if x_client_platform and x_client_platform.lower() == "ios":
        from app.services.apple_maps import get_apple_maps_service
        svc = get_apple_maps_service()
        if svc is not None:
            return svc
    return get_google_maps_service()
```
Replace the three duplicated helper bodies with a call to this (keep their thin
`Header(None)` dependency wrappers for FastAPI injection).

### 2. Travel-time abstraction on `BaseMapService` (Google unchanged, Apple = etas)

**`backend/app/services/google_maps/base.py`** — add two methods with directions-based
defaults so Google keeps its exact current behavior:
```python
async def travel_eta(self, origin, destination, *, user_id=None, trip_id=None) -> Optional[RouteLegResult]:
    route = await self.directions([origin, destination], user_id=user_id, trip_id=trip_id)
    return route.legs[0] if route and route.legs else None

async def travel_etas(self, origin, destinations, *, user_id=None, trip_id=None) -> list[Optional[RouteLegResult]]:
    return [await self.travel_eta(origin, d, user_id=user_id, trip_id=trip_id) for d in destinations]
```

**`backend/app/services/apple_maps/service.py`** — override both to call `/v1/etas`
(single-destination for `travel_eta`, batched ≤10 for `travel_etas`), mapping
`expectedTravelTimeSeconds`/`distanceMeters` → `RouteLegResult(duration_s, distance_m)`.
Leave `_directions_api_call` as the existing no-op (still never called on the iOS path).

### 3. `place_id` → lat/lng for all routing (Decision 4)

- `services/smart_ripple.py:205-211` — `_event_to_route_point()`: **drop the `place_id`
  branch**; build `RoutePoint(lat=, lng=, title=)` only. Return `None` if no coords.
- `api/endpoints/maps.py:86,220` — routability filter: require lat/lng (remove `e.place_id or`).
- `api/endpoints/maps.py:236` (and the `RoutePoint(...)` at ~89) — construct waypoints with
  lat/lng only; stop passing `place_id`. Web's Google route now snaps on coordinates
  (accurate and fully provider-agnostic).

### 4. Idempotency / enriched signal → lat/lng (Decision 6)

- `base.py:362` — `if item.get("place_id"):` → `if item.get("lat") is not None and item.get("lng") is not None:`.
- `base.py:423,469` and `api/endpoints/maps.py:412` — switch the "enriched" count/success
  check from `r.get("place_id")` to lat/lng presence, for consistency with the new
  source-of-truth. (Both Apple and Google set lat/lng on enrichment.)

### 5. `find-nearby` → platform service + batched ETAs

**`api/endpoints/concierge.py:285-359`** — add `x_client_platform: Optional[str] = Header(None)`.
- `maps_service = select_map_service(x_client_platform)` (replaces `get_google_maps_service()`
  at line 295) → `nearby_search` runs on Apple for iOS.
- Replace the per-result `directions()` loop (lines 314-330) with a single batched call:
  `legs = await maps_service.travel_etas(RoutePoint(lat=body.lat, lng=body.lng), [RoutePoint(lat=p.lat, lng=p.lng) for p in raw_places])`,
  then map each leg → `travel_time_s`/`distance_m`. Drop `place_id` from dest points.

### 6. `whats-next` → platform service + single ETA

**`api/endpoints/concierge.py:397-459`** — add `x_client_platform` header.
- `maps_service = select_map_service(x_client_platform)` (replaces line 438).
- Replace the `directions([prev_pt,next_pt])` block (lines 444-452) with
  `leg = await maps_service.travel_eta(prev_pt, next_pt, ...)`; `travel_time = leg.duration_s`.
- `prev_pt`/`next_pt` come from the updated lat/lng-only `_event_to_route_point`.

### 7. Smart Ripple → platform-threaded service (Decision 3)

- `services/smart_ripple.py` — `shift_itinerary(..., maps_service: Optional[BaseMapService] = None)`;
  at line 118 use the passed service or default to `get_google_maps_service()`.
- `_get_travel_minutes` (line 191) — call `maps_service.travel_eta(prev_point, curr_point, ...)`
  instead of `directions(...)`. (Google path = directions under the hood, unchanged behavior;
  Apple path = etas.)
- `services/concierge_executor.py` — `_shift()` and `execute()` accept/thread an
  `x_client_platform` (or a pre-selected `maps_service`), select via `select_map_service`,
  and pass it into `shift_itinerary`.
- Concierge endpoints that reach `execute()`/`_shift` (the main execute endpoint and
  `skip-event` is no-op for ripple but the shift intent flows through `execute`) plus the
  direct `/shift` endpoint in `api/endpoints/events.py` — add the `x_client_platform` header
  and pass it down.

### 8. Refresh Route button — already correct, verify only

- **iOS**: `TripDetailStore.refreshRoute` → `RouteService.computeRoute` (MKDirections) →
  `/route/save`. Already Apple-only. **No change.**
- **Web**: `GoogleMap.tsx handleRefresh` → `POST /maps/route` → Google. **No change.**

### 9. Photos / UI graceful empty (Decision 5) — verify only

- iOS `IdeaRow.swift` already guards `if let url = idea.photoUrl`. Confirm event/place cards
  on **web** also render a placeholder when `photo_url` is null/empty. Add a fallback only if
  a gap is found. No backend change.

---

## Files changed

| File | Change |
|---|---|
| `backend/app/services/maps_selector.py` *(new)* | `select_map_service(platform)` |
| `backend/app/services/google_maps/base.py` | Add `travel_eta` / `travel_etas` defaults; idempotency + enriched-count → lat/lng |
| `backend/app/services/apple_maps/service.py` | Override `travel_eta`/`travel_etas` via `/v1/etas` |
| `backend/app/services/smart_ripple.py` | `_event_to_route_point` → lat/lng only; `shift_itinerary` takes `maps_service`; use `travel_eta` |
| `backend/app/services/concierge_executor.py` | Thread platform → `shift_itinerary` |
| `backend/app/api/endpoints/concierge.py` | `find-nearby` + `whats-next`: platform service + etas |
| `backend/app/api/endpoints/maps.py` | Routing waypoints + re-enrich → lat/lng only |
| `backend/app/api/endpoints/events.py` | `/shift`: add platform header, select service |
| `backend/app/api/endpoints/{maps,brainstorm,llm}.py` | Delegate existing helpers to `select_map_service` |

No new DB migration (Decision 4 avoids schema change). No iOS or web client changes required
(`X-Client-Platform: ios` already sent on every iOS request; routing/refresh already native).

---

## Verification

1. **Enrichment (already-fixed gate):** From iOS, run Plan-Trip + Brainstorm Extract →
   confirm `lat/lng` populated and Apple Maps calls in logs, no `missing_api_key`.
2. **find-nearby (iOS):** Logs show `nearby_search` + **one** `/v1/etas` call (not N
   directions). Results carry coords + `travel_time_s`. From web: Google path unchanged.
3. **whats-next (iOS):** One `/v1/etas` call for the current→next leg; web uses Google.
4. **Smart Ripple (iOS):** Trigger a concierge shift from iOS → ripple travel-times computed
   via Apple etas (logs), events shift correctly. From web → Google. Cross-platform: an
   iOS-enriched (Apple-MUID) event shifted on **web** must succeed (routing uses lat/lng, no
   MUID sent to Google).
5. **Route render parity:** iOS route (MKDirections → `/route/save`) then open the same trip
   on **web** → stored `encoded_polyline` renders. Web route (`/maps/route` Google) → open on
   **iOS** → renders.
6. **Pins cross-platform:** Item enriched on either platform shows its pin on both (lat/lng).
7. **Photos:** Web-enriched item shows a Google photo on both platforms; iOS-enriched item
   shows the placeholder on both (no crash/broken image).
8. **Tests:** `pytest tests/ -k "enrich or apple_maps or maps or ripple or concierge"`.
   Add unit tests for `travel_etas` batching/chunking and the Apple etas response mapping.
   (Pre-existing unrelated failure in `test_intg_brainstorm_map_enrichment.py::
   test_brainstorm_extract_calls_enrich_items` was failing before this work.)
