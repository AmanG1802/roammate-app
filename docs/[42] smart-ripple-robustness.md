# Smart Ripple Engine — Robustness & Bug-Fix Plan

## Context

The Smart Ripple Engine (`backend/app/services/smart_ripple.py`) shifts itinerary
events when one moves ("running late"), cascading the shift to later events while
respecting real Google Directions travel times. It has not been touched since the
**datetime rearchitecture** (commit `7d0da64`, the split of `day_date`/`start_time`/
`end_time` into `DATE` + `TIME` columns with `combine_in_tz`/`split_in_tz`).

Good news first: **the datetime migration itself is clean here.** `_apply_shift`
correctly round-trips `(day_date, start_time, trip.tz) → UTC → (day_date, start_time)`
via `app/utils/tz.py`, preserves duration, and rejects cross-midnight shifts. No
date/time drift bugs remain in the shift math.

The real problems are elsewhere: a concierge integration that silently does nothing,
an authorization inconsistency, a dirty-session-on-error path, near-zero integration
test coverage of the cascade, and request-path performance from N sequential blocking
Directions calls. This plan fixes correctness bugs and hardens the engine for the
50k-user scale target (RM-046) **without** changing the elastic compression policy,
without adding overnight/cross-day/transport-mode capabilities, and keeping ripple
manual/concierge-only (no auto-trigger on mutations) — per product decisions.

---

## Part A — Correctness Bugs

### A1 (High) — `find_nearby` ripple is effectively a no-op
`concierge_executor.py:350-357`. After inserting a place `P` between events A and B,
it calls the engine with `delta_minutes=0` and `start_from_time = P.end_time`. Because
the anchor is selected as the first event with `start >= start_from_time`, the anchor
becomes **B, not P** — so the critical `P → B` travel leg is never evaluated. And with
`delta=0` nothing moves, so the very first gap check passes and the loop `break`s
immediately (`smart_ripple.py:136-137`). Net effect: dropping a nearby place between
two events does **not** push B later to make room for travel to/from `P`, defeating the
entire purpose of the call.

**Fix:** anchor on the inserted event itself —
`shift_itinerary(..., delta_minutes=0, start_from_event_id=event.id)`. With `P` as the
anchor, the loop's `prev` starts at `P` and the `P → B` leg is evaluated, pushing B (and
cascading) when travel exceeds the gap. Also filter the unchanged anchor out of the
returned `shifted` list when `delta_minutes == 0` and its time was unchanged, so the UI
doesn't report `P` as "adjusted."

### A2 (High) — Authorization inconsistency between REST and concierge
The REST endpoint gates ripple behind `require_trip_admin` (`events.py:335`), but the
concierge paths (`_shift` at `concierge_executor.py:167-190` and `_add_nearby`) call
`smart_ripple_engine.shift_itinerary` with **no role check**. A non-admin trip member is
blocked at the endpoint (403) yet can trigger the identical mutation through chat.

**Fix:** centralize the rule and apply it to both paths. Recommended: introduce
`require_trip_editor` (any member with edit rights, not view-only) alongside the existing
`require_trip_admin` (wherever `require_trip_admin` lives — same module), since "running
late" is a real-time member action, and apply it to the REST endpoint and the concierge
`shift_timeline` / `find_nearby` intents. (If you'd rather keep ripple admin-only, gate
the concierge intents with `require_trip_admin` instead — the point is they must match.)

### A3 (Med) — Dirty session left behind on error
On `CrossMidnightShiftError`, `_apply_shift` raises **after** earlier events in the loop
were already mutated in-memory (`smart_ripple.py:113-143`); the engine never commits, but
it also never rolls back, leaving dirty objects attached to the session. The endpoint
catches it (`events.py:363`) and returns 422, and the generic `except` (`events.py:374`)
returns 500 — neither rolls back.

**Fix:** in `shift_itinerary`, wrap the anchor+cascade mutations and on
`CrossMidnightShiftError` (and any exception) call `await db.rollback()` before
re-raising, so in-memory shifts are expired and the session is clean. Add a regression
test asserting no events persisted after a 422.

### A4 (Med) — `start_from_event_id` silent no-op
If the targeted event is locked, skipped, untimed, or on a different trip, it's filtered
out of `all_events` and `anchor_idx` is `None`, so the engine returns `[]`
(`smart_ripple.py:94-100`). Concierge `_shift` then reports "No events needed shifting"
(`concierge_executor.py:181-182`) — misleading; the user asked to shift from a specific
event and got a success message implying nothing was wrong.

**Fix:** distinguish "target not eligible / not found" from "nothing to shift." Look the
target up unfiltered to produce a precise message ("That event is locked — unlock it to
shift from there," etc.), or raise a typed error the concierge surfaces.

### A5 (Low) — Misleading ripple notification payload
The `RIPPLE_FIRED` payload reports `request.delta_minutes` (`events.py:355`), but under
elastic compression each event shifts by a *different* amount and most by less than the
delta. Keep `shifted_count`; drop or rename `delta_minutes` to avoid implying every event
moved by that amount.

### A6 (Low) — Stale docstring
`concierge_executor.py` header comment still claims "All datetimes are stored as UTC-aware
TIMESTAMPTZ" — false since the `DATE`/`TIME` split. Update so future readers don't
re-introduce drift.

---

## Part B — Robustness & Hardening

### B1 — Make same-day scoping explicit
The query orders events across **all** trip days (`smart_ripple.py:65-79`); today the
cascade only stays within one day *by accident* — the long overnight gap trips the
`available_gap >= needed_gap` break. That's fragile (two tightly-packed adjacent days, or
a missing-location night gap of 0 travel, could bleed across midnight). Since v1 is
same-day, make it explicit: after choosing the anchor, restrict the cascade to events with
`day_date == anchor.day_date` (or `break` when `curr.day_date != anchor.day_date`). This
also avoids pointless cross-day Directions calls.

### B2 — Travel-time performance & resilience (matters at 50k scale)
`shift_itinerary` issues up to **N sequential, blocking, un-timed** Directions calls per
ripple inside the HTTP request (`smart_ripple.py:120-126`). At scale this is latency + cost
+ a hang risk if Maps is slow.
- **Reuse stored `DayRoute` leg durations** when the day's waypoint set is unchanged
  (the route legs/`duration_s` already exist — see `app/api/endpoints/maps.py` route +
  `waypoint_fingerprint`), instead of re-calling Directions.
- **Bound each call** with `asyncio.wait_for(...)` and fall back to the stored leg / `0`
  on timeout, so one slow leg can't stall the request.
- **Memoize within a call** by `(origin_key, dest_key)` so repeated legs aren't recomputed.

### B3 — Optional: departure-time-aware durations
Pass the previous event's end instant as `departure_time` to Directions so cascades use
traffic-aware durations rather than free-flow. Keep driving mode (transport modes are out
of scope). Implement only if `google_maps.directions` already supports it cheaply;
otherwise log as a follow-up.

### B4 — Surface bad `trip.timezone`
`trip_tz` silently falls back to `"UTC"` when missing/invalid (`smart_ripple.py:63`),
which makes the cross-midnight check use UTC midnight instead of local. Log a warning when
`trip.timezone` is unset/invalid so corrupt trip data is visible in observability.

### B5 — Optional: serialize concurrent ripples
Two concurrent ripples on the same trip can interleave reads/writes. Add a
`SELECT ... FOR UPDATE` on the trip's events (or a trip-scoped advisory lock) so they
serialize. Lower priority; include if the scale-hardening work (RM-046) already favors it.

---

## Part C — Test Coverage (the biggest gap)

Today only `_apply_shift`/`_event_to_route_point` (unit, `tests/unit/test_smart_ripple.py`)
and the **legacy** engine (`tests/services/test_ripple_engine.py`) are tested. The actual
`SmartRippleEngine.shift_itinerary` cascade has **no** integration coverage. Add tests
(new `tests/api/test_api_*.py` per the in-progress layout, plus a service-level file)
with a **mocked `maps_service.directions`**:

- Single-anchor shift; multi-event cascade with travel time.
- Gap-stop: a roomy gap halts propagation (`break`).
- Overlap/zero-travel: anchor pushed into next event de-overlaps it.
- `start_from_event_id` path; locked/skipped/untimed events excluded; **non-eligible
  target returns a reason** (A4 regression).
- Timezone-aware cascade (IST trip) and a DST-boundary date.
- Cross-midnight → endpoint **422 end-to-end** and **no events persisted** (A3 regression).
- **`find_nearby` end-to-end**: inserting a place pushes the next event when travel
  exceeds the gap (A1 regression).
- Authorization parity: non-admin/editor blocked on both REST and concierge (A2).

---

## Out of Scope (per decisions)
- Rigid "shift-all by delta" policy — **keeping elastic compression** as-is.
- Overnight / cross-day cascades; transport modes beyond driving.
- Auto-ripple on event create/update/delete — ripple stays manual + concierge.
  (Document this as intentional in the engine docstring.)

---

## Files to Modify
- `backend/app/services/smart_ripple.py` — B1 (day scoping), B2/B3 (travel reuse/timeout/
  departure), B4 (tz warning), A3 (rollback), A4 (eligibility reason), B5 (optional lock).
- `backend/app/services/concierge_executor.py` — A1 (`find_nearby` anchor fix), A2 (auth on
  intents), A4 (message), A6 (docstring).
- `backend/app/api/endpoints/events.py` — A2 (shared editor gate), A3 (rollback in
  `except`), A5 (notification payload).
- Roles/deps module that defines `require_trip_admin` — add `require_trip_editor`.
- `backend/app/services/google_maps.py` — only if B3 departure_time / B2 timeout needs a
  signature change.
- `backend/tests/api/` + `backend/tests/services/` — Part C tests.

## Verification
1. **Targeted tests:** `cd backend && pytest tests/ -k "ripple or smart_ripple or find_nearby" -q`
   — all new + existing ripple tests green.
2. **Full suite:** `cd backend && pytest -q` — confirm no regressions across the ~480 tests.
3. **Manual `find_nearby` (A1):** with two tightly-spaced events far apart geographically,
   add a nearby place via concierge and confirm the later event is pushed (it is currently
   not). Use the `debug-db` skill to inspect persisted `start_time`s before/after.
4. **Manual 422 (A3):** fire a ripple large enough to cross midnight; confirm 422 with the
   structured detail **and** that re-fetching the trip shows no partial shifts persisted.
5. **Auth parity (A2):** as a non-admin member, attempt the REST ripple (expect block) and
   the concierge "shift my day" intent (expect the same outcome).
