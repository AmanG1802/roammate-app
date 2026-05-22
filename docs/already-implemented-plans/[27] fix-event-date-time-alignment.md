# [27] Split event date and time-of-day in storage

## Context

`TimelineItem.day_date` (ISO string) and `start_time`/`end_time` (tz-aware UTC datetimes) are written and updated independently, so the calendar date inside `start_time` drifts away from `day_date`. Two known producers:

1. **Idea → timeline promotion** (`ios/.../AddToTimelineSheet.swift:139-141`): `dayDate` is rebased to the chosen day, but `idea.startTime` / `idea.endTime` pass through verbatim. Ideas created via `POST /events/{id}/move-to-bin` (`events.py:241-246`) were redated to **today UTC**, so promoting one to a different day creates an event whose `start_time` is on the wrong calendar day — the trip 27 bug (`day_date=2026-05-18`, `start_time=2026-05-17 04:30Z`).
2. **Trip start-date shift** (`backend/app/api/endpoints/trips.py:295-332`): the loop rebases `evt.day_date` by `delta` but never moves `evt.start_time` / `evt.end_time`.

Why it bites now: `TodayWidgetCards` groups by `day_date` but filters by `start_time/end_time` (`TodayWidgetCards.swift:161, 174-180`). When the two disagree, the widget body goes empty.

We're fixing this at the **schema level** rather than patching every write site, so the bug class disappears. Times are stored without a date component; the date lives only in `day_date`. Render is in the **trip's timezone** (an itinerary "10:00 in Tokyo" should always read 10:00 regardless of where the user opens the app). Overnight events are out of scope for v1 (see Future scope).

## Approach

### Phase 0 — prerequisite: make `Trip.timezone` accurate

Today `Trip.timezone` is captured **once at trip creation** from the device's `TimeZone.current.identifier` (`ios/.../CreateTripView.swift:99`, `PlanTripStore.swift:76`, `PlanTripService.swift:9`; web `frontend/lib/store.ts`). A user planning a Tokyo trip from NYC ends up with `America/New_York` — the "render in trip tz" semantics would then show the wrong wall-clock. Two fixes, both required before the migration backfills using `AT TIME ZONE Trip.timezone`:

1. **Infer from destination at plan_trip time.** After the LLM returns `map_output` and items are geocoded (existing flow), pick the first item with valid `(lat, lng)` and call the [Google Maps Time Zone API](https://developers.google.com/maps/documentation/timezone) (`https://maps.googleapis.com/maps/api/timezone/json?location=<lat>,<lng>&timestamp=<unix>`). The returned `timeZoneId` (e.g. `"Asia/Tokyo"`) becomes the trip's timezone, overriding the device tz the client sent. Wire this in `backend/app/api/endpoints/brainstorm.py` around the trip-creation point (line 328 area) and/or `backend/app/services/google_maps/v2.py` as a new `timezone_for(lat, lng)` method that uses the existing httpx client + `GoogleMapsApiUsage` cost tracking. Cache by rounded `(lat, lng)` cell to avoid repeat calls for items in the same city.
2. **Surface a tz picker** in `CreateTripView` (manual-create path) and the trip edit sheet (`TripLandingView.swift:332` currently passes `timezone: nil` — change to send the chosen value). Default to device tz; allow override. Same picker on the web `frontend/app/trips/page.tsx` create flow. This handles trips that aren't created via plan_trip.

Without Phase 0 the migration backfill would convert UTC datetimes into the *wrong* trip-local time and the bug visibly persists for cross-tz trips.

### Types at every layer

| Concept | Postgres | SQLAlchemy | Pydantic | JSON wire | Swift | TypeScript |
|---|---|---|---|---|---|---|
| `day_date` | `DATE` | `Date` | `datetime.date` | `"YYYY-MM-DD"` | `Date` (00:00 in tripCal) via existing parser | `string` |
| `start_time` / `end_time` | `TIME` (no tz) | `Time(timezone=False)` | `datetime.time` | `"HH:MM:SS"` (no microseconds) | `TimeOfDay` struct (Codable) | `string` |
| `Trip.timezone` | unchanged `String` | unchanged | unchanged | unchanged | unchanged | unchanged |

Wire-format details:
- Force Pydantic `time` serialization to `"%H:%M:%S"` via a model serializer to avoid optional microseconds — keeps Swift/JS parsers simple and lexicographic sort safe.
- Date wire format already `"YYYY-MM-DD"` (today it's a `String` column); the type tightening just adds parse/validate guarantees.

### Cascading sites (full audit)

Backend — every site reading or writing `start_time`/`end_time` (123 hits):

- `backend/app/schemas/event.py:22-56` — `EventCreate` / `EventUpdate` field types + the existing `@field_validator` (tz-coerce-to-UTC) becomes a "no tzinfo on time" guard.
- `backend/app/schemas/trip.py:66-67` — `IdeaBinItem` schema.
- `backend/app/schemas/dashboard.py:13-14` — dashboard EventOut.
- `backend/app/schemas/library.py:36-37` — **keep as `Optional[str]`**. Add a docstring noting canonical wire format is `"HH:MM:SS"`. Rationale: this is an output view serialized via `str(idea.start_time)` in `groups.py:541-542`; once the column is `Time`, that cast naturally produces `"HH:MM:SS"`. No validation lost.
- `backend/app/schemas/concierge.py:55,61-62` — **keep as `Optional[str]`**. Add a docstring noting these are LLM-tool param shapes that accept loose forms (`"4pm"`, `"16:00"`, `"morning"`) and rely on a downstream normalizer before hitting event endpoints. Tightening to `time` would 422 on the LLM's natural emissions and regress flexibility. Validation belongs at the parser boundary, not here.
- `backend/app/api/endpoints/maps.py` — **biggest consumer; full rewrite of conflict detection**:
  - Line 78, 147, 177 sorts use `e.start_time or datetime.min` → switch to `(e.day_date or date.min, e.start_time or time.min)` tuples.
  - Lines 101-107 `prev.end_time > curr.start_time` conflict check needs combining `(day_date, time, trip.timezone) → datetime` then comparing. Conflict semantics may also tighten now that overnight is disallowed (same-day comparisons only in v1).
  - Lines 88-89 `.isoformat()` output for routing payload.
- `backend/app/api/endpoints/dashboard.py:124,131-132,142` — uses `ensure_utc()`; replace with `(day_date, time)` carried through; "ongoing/upcoming" combines with `Trip.timezone`.
- `backend/app/api/endpoints/concierge.py:74` — `.isoformat()` serializer; switch to `time.isoformat()`.
- `backend/app/api/endpoints/groups.py:541-542` — already `str(idea.start_time)`; will become `time.isoformat()` naturally.
- `backend/app/api/endpoints/brainstorm.py:394-395` — seeding `start_time=start, end_time=end` from LLM output; switch to `time` values.
- `backend/app/api/endpoints/ideas.py:70-71` — idea → event copy; trivial type swap.
- `backend/app/api/endpoints/events.py:63,64,147-151,251-252` — covered above (create/update + `_redate` deletion).
- `backend/app/services/smart_ripple.py` — **second biggest rewrite**:
  - Lines 48, 53, 59-60 prefilter and `ensure_utc` go away.
  - Lines 74, 84-86, 99-104, 110-112 do `+= timedelta` and `>=` comparisons. Each must (a) combine `(day_date, time)` in `Trip.timezone` to a UTC instant, (b) do the math, (c) split back. If the new time crosses midnight in trip-local terms, return the structured rejection from the plan.
- `backend/app/services/notification_service.py` and payload templates — anywhere an event time is embedded in a notification body.
- `backend/tests/` — every fixture and assertion using `datetime(...)` for event times → `time(...)`. (count after grep; expect 30-50 touches.)
- **Alembic migration** — add CHECK constraint; consider composite index `(trip_id, day_date, start_time)` to keep dashboard queries fast.
- **`time_category`** stays untouched; it remains the fallback when `start_time IS NULL`. Document this so nobody invents a new convention.

iOS — 71 hits:

- `ios/Roammate/Models/Event.swift:27-50, 76-128` and `Models/IdeaBinItem.swift:23-62` — replace `Date?` with `TimeOfDay?` (new value type, Codable as `"HH:mm:ss"`). Custom `init(from:)`/`encode(to:)` since Swift `JSONDecoder` date strategies don't apply to a non-Date type.
- New `ios/Roammate/Models/TimeOfDay.swift` — `(hour, minute, second)` with `combine(day: Date, tz: TimeZone) -> Date` for instant-needs.
- `ios/Roammate/Network/RouteService.swift:139, 399` — sort comparator: `Date < Date` → `TimeOfDay < TimeOfDay` (or `(dayDate, timeOfDay)` tuple).
- `ios/Roammate/Network/RouteService.swift:411-412` — **local fingerprint only**, not a backend payload. `computeFingerprint` hashes parts into a SHA prefix for routing-cache invalidation; nothing leaves the device. Swap the `ISO8601DateFormatter` line for `TimeOfDay.formatted()` (and include `dayDate` for completeness). Fingerprint changes once across the schema swap → one stale cache miss per device, negligible. No backend coordination needed.
- `ios/Roammate/Views/Dashboard/TodayWidgetCards.swift:175-191` — "ongoing/upcoming" filter combines `(today, time, trip.timezone)` once, then comparisons against `Date()`.
- `ios/Roammate/Views/Trips/Plan/IdeaRow.swift:20-21, 80-81, 231` — SwiftUI `DatePicker(.hourAndMinute)` returns `Date`; add a small `Date <-> TimeOfDay` adapter (today-anchored just for the picker).
- `ios/Roammate/Views/Trips/Plan/AddToTimelineSheet.swift:140-141` — trivial type swap.
- `ios/Roammate/Views/Trips/Plan/TimelineRow.swift:13` — `startTimeText` formatter switches from `DateFormatter` to `TimeOfDay.formatted()`.
- Plus the remaining ~30 iOS hits (all renderers / sorts / fixtures).

Web — see Web section below.

### Storage model

- `TimelineItem.start_time`, `TimelineItem.end_time` → **`TIME` (no tz)**, interpreted as **trip-local wall-clock**.
- `TimelineItem.day_date` → **`DATE`** (currently `String`; tighten the column).
- `IdeaBinItem.start_time`, `IdeaBinItem.end_time` → same `TIME`, no `day_date`.
- `Trip.timezone` (`all_models.py:69`, default `"UTC"`) remains the single source of truth for converting `(day_date, time)` → an absolute instant when needed (push reminders, ICS export, conflict detection).

Why trip-local wall-clock and not UTC: with a TIME-only column, "UTC time + trip-tz date" doesn't combine cleanly across midnight in the trip tz, and renderers need an extra conversion they can't perform without `Trip.timezone` in hand at every call site. Trip-local storage means the values render correctly with no conversion in the common path and only need `Trip.timezone` when computing an absolute instant.

### Invariants enforced by the schema

- An event cannot have a time that contradicts its day — the date simply isn't part of the time.
- An idea has a `time` but no `day_date`; promotion attaches the chosen `day_date`.
- `end_time >= start_time` (validated at the API layer). Equal allowed for instantaneous markers. Overnight (end < start) rejected — see Future scope.

### Backend changes

**Models** (`backend/app/models/all_models.py`):
- `TimelineItem.start_time`, `end_time`: `Column(Time, nullable=True)`.
- `TimelineItem.day_date`: `Column(Date, nullable=True, index=True)`.
- `IdeaBinItem.start_time`, `end_time`: `Column(Time, nullable=True)`.

**Schemas** (`backend/app/schemas/event.py`, `backend/app/schemas/trip.py`):
- `Event.start_time` / `end_time`: `datetime.time | None`. `day_date`: `datetime.date | None`.
- Same for `EventCreate`, `EventUpdate`, `IdeaBinItem`, `IdeaBinItemCreate`.
- Pydantic validator: reject `end_time < start_time` with a clear "overnight events not supported in v1" message.

**Endpoints** (`backend/app/api/endpoints/events.py`):
- `create_event` (line 43): drop all date-from-time juggling; just pass the fields through.
- `update_event` (line 120): same — independent assignment is now safe.
- `move_event_to_bin` (line 219): delete `_redate` (lines 241-246) entirely; copy `start_time`/`end_time` straight across.

**Trip shift** (`backend/app/api/endpoints/trips.py:295-332`):
- Keep the `evt.day_date` rebase by `delta`; the `start_time`/`end_time` lines that today's plan would have added are no longer needed because times have no date.

**Ripple engine** (`backend/app/services/smart_ripple.py`):
- Combine `(evt.day_date, evt.start_time)` in `Trip.timezone` to an instant when computing shifts, then split back to `(day_date, time)` after the shift.
- For v1: if a shift would push an event past midnight (i.e., `day_date` would need to change), **reject the shift** with a structured error the UI can show. This keeps the no-overnight invariant. Document the limitation in the function docstring.

**Brainstorm / plan_trip pipeline** (`backend/app/services/llm/services/v1/roammate_v1.py`):
- LLM still returns `time_category`; the conversion that today produces a UTC datetime instead produces a `time` (no date) or leaves it null. No tz reasoning needed.

### Migration

Alembic migration `backend/alembic/versions/xxxx_split_event_date_time.py`:

1. Add `start_time_new` (TIME), `end_time_new` (TIME), `day_date_new` (DATE) to `timeline_item`. Add `start_time_new`, `end_time_new` (TIME) to `idea_bin_item`.
2. Backfill `timeline_item`:
   ```sql
   UPDATE timeline_item ti
   SET day_date_new = ti.day_date::date,
       start_time_new = (ti.start_time AT TIME ZONE COALESCE(t.timezone, 'UTC'))::time,
       end_time_new   = (ti.end_time   AT TIME ZONE COALESCE(t.timezone, 'UTC'))::time
   FROM trip t
   WHERE ti.trip_id = t.id;
   ```
   (`AT TIME ZONE <tz>` on a `timestamptz` returns the local wall-clock at that tz as a naïve timestamp; cast to `time` keeps the time-of-day.)
3. Backfill `idea_bin_item` similarly (using its trip's timezone).
4. Drop old `start_time`, `end_time`, `day_date` columns; rename `*_new` → original names.
5. Add CHECK constraint `end_time IS NULL OR start_time IS NULL OR end_time >= start_time` on both tables.

User has explicitly said: do not worry about backward compat with existing production data — the SQL above is still correct (and produces the time the user has been seeing on-screen, since that was always rendered in their local tz).

### iOS changes

**Model** (`ios/Roammate/Models/Event.swift` and `IdeaBinItem` equivalent):
- `startTime`, `endTime`: change from `Date?` to `TimeOfDay?` (a small struct wrapping `(hour: Int, minute: Int)`, Codable as `"HH:mm:ss"` to match Postgres `TIME`).
- `dayDate`: keep as the parsed calendar date.

**Renderers** — every site that formats `event.startTime` as a time must now combine with the trip's timezone for instant-based logic, but for pure time-of-day display it just reads `timeOfDay.formatted()`. Sites to audit (non-exhaustive, full sweep during impl):
- `TodayWidgetCards.swift:160-220` — "ongoing/upcoming" check needs `(today's day_date, time, trip.timezone) → Date` then compare to `Date()`.
- `AddToTimelineSheet.swift:120-150` — pass `idea.timeOfDay` through; no date construction.
- Timeline view sort: by `(dayDate, startTime)` lexicographic.
- Ripple UI, conflict UI, calendar/event detail editors.

**Trip tz plumbing**: `Trip.timezone` already exists on the iOS model (verify). Anywhere we need an absolute instant, combine via `Calendar(identifier: .gregorian)` with `TimeZone(identifier: trip.timezone)`.

### Web frontend (Next.js) changes

Same shape of bug surface as iOS — `frontend/lib/store.ts:32-34, 170-172, 192-195` consumes `start_time`/`end_time` as `Date` and `day_date` as string. Mirror the iOS changes:

- `frontend/lib/store.ts`:
  - `Event.start_time` / `end_time`: `Date | null` → `string | null` (`"HH:mm:ss"`).
  - New `frontend/lib/time.ts` with `parse`, `format`, and `combine(dayDate, time, tz) → Date` for absolute-instant needs.
  - `sortEvents` (~line 192): compare `(day_date, start_time)` lexicographically (fixed-width `HH:mm:ss` sorts correctly).
  - `makeLocalEvent` (~line 10) and `moveIdeaToTimeline` (~line 241): stop synthesizing `new Date(...)` for the +1h default; produce a `"HH:mm:ss"` string instead.
- Renderers to audit (same diff shape each):
  - `frontend/components/dashboard/TodayWidget.tsx` — mirror iOS "ongoing/upcoming" filter via `combine(dayDate, time, trip.timezone)`.
  - `frontend/components/trip/Timeline.tsx` — sort and render.
  - `frontend/components/trip/IdeaBin.tsx`, `ConciergeActionBar.tsx`, `ConciergeChatDrawer.tsx`, `GroupsPanel.tsx`, `components/map/GoogleMap.tsx`, `app/trips/page.tsx`.
- Create-trip / edit-trip on web: add the tz picker per Phase 0.
- Test fixtures in `frontend/tests/`: update event shape.

### API contract

- `start_time`/`end_time` in request/response bodies become `"HH:mm:ss"` strings instead of ISO datetimes.
- `day_date` becomes `"YYYY-MM-DD"` (same as today's string form, just typed as `date`).
- Mobile clients ship updated, but since we control the only client and there are no in-flight production users blocked by this, no version negotiation needed.

## Files to modify

**Phase 0 (Trip.timezone accuracy):**
- `backend/app/services/google_maps/v2.py` — new `timezone_for(lat, lng)` using the Google Time Zone API; cache by rounded cell; record cost via `GoogleMapsApiUsage`.
- `backend/app/api/endpoints/brainstorm.py:328` area — after items are geocoded, infer `Trip.timezone` from first valid `(lat, lng)` and override the client-provided value.
- `ios/Roammate/Views/Trips/CreateTripView.swift` + trip-edit (`TripLandingView.swift:332`) — tz picker.
- `frontend/app/trips/page.tsx` create + edit — tz picker.

**Schema split:**
- `backend/app/models/all_models.py` — TimelineItem (lines 231-244), IdeaBinItem (lines 132-138).
- `backend/app/schemas/event.py`, `backend/app/schemas/trip.py` — type changes + overnight validator.
- `backend/app/api/endpoints/events.py` — create/update/move-to-bin simplifications.
- `backend/app/api/endpoints/trips.py:295-332` — keep `day_date`-only shift loop.
- `backend/app/services/smart_ripple.py` — combine/split with trip tz; reject cross-midnight shifts.
- `backend/app/services/llm/services/v1/roammate_v1.py` — return `time` not datetime.
- **NEW** `backend/alembic/versions/xxxx_split_event_date_time.py`.
- `ios/Roammate/Models/Event.swift` (+ IdeaBinItem) — new `TimeOfDay` type.
- `ios/Roammate/Views/Dashboard/TodayWidgetCards.swift:160-220`.
- `ios/Roammate/Views/Trips/Plan/AddToTimelineSheet.swift:120-150`.
- iOS timeline / ripple / conflict views (audit during impl).

**Web frontend:**
- `frontend/lib/store.ts` — model + sort + makeLocalEvent + moveIdeaToTimeline.
- **NEW** `frontend/lib/time.ts` — `TimeOfDay` helpers.
- `frontend/components/dashboard/TodayWidget.tsx`, `components/trip/Timeline.tsx`, `IdeaBin.tsx`, `ConciergeActionBar.tsx`, `ConciergeChatDrawer.tsx`, `GroupsPanel.tsx`, `components/map/GoogleMap.tsx`, `app/trips/page.tsx`.
- `frontend/tests/` fixtures.

## Reused / existing

- `Trip.timezone` (`all_models.py:69`) — already populated; becomes more load-bearing.
- `PlaceColumnsMixin` and the rest of `TimelineItem` / `IdeaBinItem` columns — unchanged.
- iOS `EventService.isoDateString(from:)` — still used for `day_date`.

## Verification

1. **Migration** on a copy of local DB:
   - Pre: trip 27's rows 157/158/159 show `day_date=2026-05-18`, `start_time=2026-05-17 04:30Z`.
   - Post: rows show `day_date=2026-05-18`, `start_time=10:00:00`, `end_time=11:00:00` (IST wall-clock).
   - Trip with `timezone='UTC'` round-trips times unchanged.
2. **API smoke**: reproduce the trip 27 bug:
   - Create trip in IST, run plan_trip, move event to bin, promote to Day 3.
   - Returned event has `day_date=2026-05-19`, `start_time=10:00:00`. Re-fetch confirms.
3. **Trip-shift regression**: PATCH trip start_date forward by 2 days. Every event's `day_date` shifts by +2; `start_time`/`end_time` are unchanged. Render still shows the same wall-clock time.
4. **Dashboard widget** (iOS + web): as `amanngupta01@gmail.com`, both widgets show trip 27's Day 2 items at the right times.
4b. **Phase 0 tz inference**: create a new trip via `plan_trip` with a Tokyo prompt from an NYC-tz client → `Trip.timezone == "Asia/Tokyo"` in the DB.
5. **Overnight rejection**: POST an event with `start_time=22:00`, `end_time=02:00` → 422 with a clear message.
6. **Ripple at boundary**: shift an event from 23:30 by +60 min → ripple returns a structured error instead of silently producing bad data.

## Future scope

**Overnight events.** v1 disallows `end_time < start_time`. To support them later, the most contained extension is:

- Add an optional `end_day_offset: int = 0` column (or `Boolean ends_next_day`) to TimelineItem so a single row can span midnight without re-introducing dates into `start_time`/`end_time`.
- Update conflict / overlap detection to combine `(day_date, start_time)` and `(day_date + end_day_offset days, end_time)` in trip tz.
- Update ripple to allow shifts that change `end_day_offset` (and, eventually, `day_date` itself) when the source is explicitly marked overnight; otherwise keep rejecting cross-midnight shifts.
- Update the LLM prompts in `roammate_v1.py` to emit `end_day_offset` for things like red-eye flights, late-night clubbing, multi-day road segments.
- iOS: render overnight events with a "→ next day" affordance in the timeline; the day-2 widget shows the tail.

This is a localized addition on top of the v1 schema, not a rewrite — which is the main reason to do the split now even though overnight is deferred.
