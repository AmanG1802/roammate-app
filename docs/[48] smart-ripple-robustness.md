# Smart Ripple Engine — Robustness & Bug-Fix Plan

## What is the Smart Ripple Engine?

The Smart Ripple Engine (`backend/app/services/smart_ripple.py`) is Roammate's
travel-time-aware itinerary re-scheduler. When one event on a trip day runs late (or is
explicitly shifted), the engine cascades that shift to every subsequent event on the same
day, but **only when the gap between consecutive events is smaller than the actual driving
time between them** — as returned by the Google Directions API. Events with sufficient
buffer are left alone and the cascade stops.

### Responsibilities

- Compute real driving durations between consecutive timeline events using Google Maps Directions.
- Apply a delta shift to an anchor event and ripple it forward, stopping the cascade as soon as a sufficient gap is found.
- Reject shifts that would push an event past midnight in the trip's local timezone (`CrossMidnightShiftError`).
- Honour locked events (never shift them) and skipped events (exclude from routing).

### How it is triggered


| Trigger                               | Entry point                         | Who can call             |
| ------------------------------------- | ----------------------------------- | ------------------------ |
| Manual "running late"                 | `POST /api/events/ripple/{trip_id}` | Trip admin only (REST)   |
| Concierge "shift my day" intent       | `ConciergeExecutor._shift()`        | Any trip member via chat |
| Concierge "find nearby + add"         | `ConciergeExecutor._add_nearby()`   | Any trip member via chat |
| *(planned A7)* Concierge "move event" | `ConciergeExecutor._move()`         | Any trip member via chat |
| *(planned A8)* Concierge "add event"  | `ConciergeExecutor._add()`          | Any trip member via chat |


### Core algorithm (`shift_itinerary`)

1. Load trip timezone (default `"UTC"` on missing/invalid).
2. Query all timed, non-skipped events for the trip, ordered by `(day_date, start_time)`.
3. Find anchor: by `start_from_event_id` or first event whose UTC start ≥ `start_from_time`.
4. Apply `delta` to anchor via `_apply_shift` (combines to UTC, adds delta, splits back to local; raises on day change).
5. Loop through subsequent events:
  - Compute driving minutes via `_get_travel_minutes` (Google Directions first leg).
  - If `available_gap >= travel_time` → stop (buffer is sufficient).
  - Else shift current event by the shortfall; continue.
6. Commit; return list of shifted events.

---

## Context

The engine has not been touched since the **datetime rearchitecture** (commit `7d0da64`,
which split `datetime` columns into `(DATE day_date, TIME start_time, TIME end_time)` with
`combine_in_tz` / `split_in_tz`). That migration is clean: `_apply_shift` correctly
round-trips through trip-local timezone and preserves event duration.

The real problems are: Concierge mutations that bypass ripple entirely, a locked-event
blind spot, an authorization inconsistency, a dirty-session-on-error path, near-zero
integration test coverage of the cascade, and request-path performance from N sequential
unretried Directions calls.

This plan fixes correctness bugs and hardens the engine for the 50k-user scale target
(RM-046) **without** changing the elastic compression policy, without adding overnight /
cross-day cascade capabilities, and keeping cross-day Concierge moves blocked (drag on
timeline instead) — per product decisions.

---

## Part A — Correctness Bugs

### A1 (High) — `find_nearby` ripple is effectively a no-op

`concierge_executor.py:350-357`. After inserting a place `P` between events A and B, it
calls the engine with `delta_minutes=0` and `start_from_time = P.end_time`. Because the
anchor is selected as the first event with `start >= start_from_time`, the anchor becomes
**B, not P** — so the critical `P → B` travel leg is never evaluated. And with `delta=0`
nothing moves, so the very first gap check passes and the loop `break`s immediately
(`smart_ripple.py:136-137`). Net effect: dropping a nearby place between two events does
**not** push B later to make room for travel to/from P, defeating the entire purpose of
the call.

**Fix:** anchor on the inserted event itself —
`shift_itinerary(..., delta_minutes=0, start_from_event_id=event.id)`. With P as the
anchor, the loop's `prev` starts at P and the `P → B` leg is evaluated, pushing B (and
cascading) when travel exceeds the gap. Also filter the unchanged anchor out of the
returned `shifted` list when `delta_minutes == 0` and its time was unchanged, so the UI
doesn't report P as "adjusted."

---

### A2 (High) — Authorization inconsistency between REST and Concierge

The REST endpoint gates ripple behind `require_trip_admin` (`events.py:335`), but the
Concierge paths (`_shift` at `concierge_executor.py:167-190` and `_add_nearby`) call
`smart_ripple_engine.shift_itinerary` with **no role check**. A non-admin trip member is
blocked at the endpoint (403) yet can trigger the identical mutation through chat.

**Fix:** introduce `require_trip_editor` (any member with edit rights, not view-only)
alongside the existing `require_trip_admin`. Apply `require_trip_editor` to the REST
endpoint and to the Concierge `shift_timeline` / `find_nearby` / `move_event` / `add_event`
intents. ("Running late" is a real-time member action, not an admin-only one.)

---

### A3 (Med) — CrossMidnightShiftError: caller-controlled commit vs rollback

When `_apply_shift` raises `CrossMidnightShiftError`, events shifted earlier in the
cascade are mutated in-memory but neither committed nor rolled back — leaving a dirty
session. The REST endpoint catches the exception (`events.py:363`) but doesn't roll back;
Concierge `_shift()` has **no catch at all** (unhandled 500).

Two callers need different behavior:

- **REST endpoint**: rollback all in-memory mutations → 422 with structured detail.
- **Concierge `_shift()` / `_move()` / `_add()`**: commit the partial shifts up to the
failing event → return "Shifted N events — [EventName] would run past midnight, so I
stopped there."

**Fix design:**

1. Add `shifted_so_far: list[Event]` field to `CrossMidnightShiftError.__init__` so
  callers know which events were already mutated.
2. `shift_itinerary` does **not** commit or rollback on error — it re-raises with the
  list attached. (Note: `_apply_shift` raises *before* mutating the failing event, so
   the list is safe to commit as-is.)
3. REST endpoint (`events.py`): catches → `await db.rollback()` → 422.
4. Concierge executor methods: catch → `await db.commit()` → return partial-success
  message using `error.shifted_so_far`.

---

### A4 (Med) — `start_from_event_id` silent no-op

If the targeted event is locked, skipped, untimed, or on a different trip, it's filtered
out of `all_events` and `anchor_idx` is `None`, so the engine returns `[]`
(`smart_ripple.py:94-100`). Concierge `_shift` then reports "No events needed shifting"
(`concierge_executor.py:181-182`) — misleading; the user asked to shift from a specific
event and got a success message implying nothing was wrong.

**Fix:** look the target up unfiltered to produce a precise message — "That event is
locked — unlock it to shift from there," "That event has no time set," etc. — or raise a
typed `EventNotEligibleError` the Concierge surfaces directly.

---

### A5 (Low) — Misleading ripple notification payload

The `RIPPLE_FIRED` payload reports `request.delta_minutes` (`events.py:355`), but under
elastic compression each event shifts by a *different* amount and most by less than the
delta. Keep `shifted_count`; drop or rename `delta_minutes` to `requested_delta_minutes`
to avoid implying every event moved by that amount.

---

### A6 (Low) — Stale docstring

`concierge_executor.py` header comment still claims "All datetimes are stored as
UTC-aware TIMESTAMPTZ" — false since the `DATE`/`TIME` split. Update so future readers
don't re-introduce drift.

---

### A7 (High) — `_move()` doesn't trigger ripple

After a Concierge move-event (new time, same day), subsequent events on that day are never
rechecked for travel-time conflicts. Only the moved event itself is returned; downstream
gaps are silently wrong.

`concierge_executor.py:192-236` — `_move()` commits and returns without calling
`shift_itinerary`.

**Fix:**

1. Add `user_id` to `_move()` signature (currently missing — needed for Maps API quota).
2. Reject cross-day moves: if `new_day_date` is provided and differs from `event.day_date`,
  return `{"success": False, "message": "Cross-day moves aren't supported via chat yet  — drag the event to the new day from the timeline."}`.
3. After committing the time change, call
  `shift_itinerary(delta_minutes=0, start_from_event_id=event.id, user_id=user_id)`.
4. Return merged `updated_events`: the moved event union the ripple-shifted events.
5. Catch `CrossMidnightShiftError` with partial commit + warning message (A3 pattern).

---

### A8 (High) — `_add()` doesn't trigger ripple

`_add()` (`concierge_executor.py:238-297`) creates an event and returns immediately with
no cascade — even when the new event is inserted between two existing events. `_add_nearby`
does call ripple (and will be fixed by A1), but the plain `add_event` Concierge intent
doesn't.

**Fix:** after committing the new event, if `event.start_time` is set, call
`shift_itinerary(delta_minutes=0, start_from_event_id=event.id, user_id=user_id)` —
identical to the corrected `_add_nearby()` pattern. Add `user_id` to `_add()` signature.
Catch `CrossMidnightShiftError` with partial commit + warning (A3 pattern).

---

### A9 (Med) — Locked events excluded as route waypoints

Locked events are filtered from `all_events` in the query (`smart_ripple.py:65-79`). When
a locked event B sits between shifted event A and unlocked event C, ripple computes travel
A → C and ignores the B → C leg entirely. If C needs 25 min from B but only has 15 min,
the conflict is silently missed.

**Fix:** change the query to load ALL timed, non-skipped events (remove the
`Event.is_locked == False` filter). In the cascade loop:

- If `curr.is_locked`: skip `_apply_shift(curr, ...)` but update `ends_utc[curr.id]`
so the next iteration uses the locked event's end time as the reference for travel
computation (locked events act as **read-only waypoints**).
- If `prev.is_locked`: its `ends_utc` is already populated; travel from locked → next
is evaluated normally.

---

### A10 (Med) — Maps API failure silently stops cascade

`_get_travel_minutes` catches any `Exception` and returns `0` on the **first** failure
(`smart_ripple.py:198-203`). With `travel_time=0`, `available_gap >= 0` is always true →
the cascade `break`s after the anchor → all subsequent events are under-shifted without
warning.

**Fix:** retry up to **3 times** with exponential backoff (100 ms, 200 ms, 400 ms) before
falling back to `0`. After 3 failures, log a structured warning (leg event IDs + trip ID)
then return `0` — preserving the existing safety net but making transient errors far less
likely to corrupt the cascade. Implement as a simple `async` retry loop in
`_get_travel_minutes`; no new library dependency needed.

---

## Part B — Robustness & Hardening

### B1 — Make same-day scoping explicit

The query orders events across **all** trip days (`smart_ripple.py:65-79`); today the
cascade only stays within one day *by accident* — the long overnight gap trips the
`available_gap >= needed_gap` break. That's fragile (two tightly-packed adjacent days, or
a missing-location night gap of 0 travel, could bleed across midnight). Since v1 is
same-day, make it explicit: after choosing the anchor, `break` when
`curr.day_date != anchor.day_date`. This also avoids pointless cross-day Directions calls.

### B2 — Travel-time performance & resilience (matters at 50k scale)

`shift_itinerary` issues up to **N sequential, blocking** Directions calls per ripple
inside the HTTP request (`smart_ripple.py:120-126`). At scale this is latency + cost + a
hang risk if Maps is slow.

- **Reuse stored `DayRoute` leg durations** when the day's waypoint set is unchanged
(the route legs/`duration_s` already exist — see `app/api/endpoints/maps.py` route +
`waypoint_fingerprint`), instead of re-calling Directions.
- **Bound each call** with `asyncio.wait_for(...)` and fall back to the stored leg / `0`
on timeout, so one slow leg can't stall the request.
- **Memoize within a call** by `(origin_key, dest_key)` so repeated legs aren't
recomputed.

### B3 — Optional: departure-time-aware durations

Pass the previous event's end instant as `departure_time` to Directions so cascades use
traffic-aware durations rather than free-flow. Keep driving mode (transport modes are out
of scope). Implement only if `google_maps.directions` already supports it cheaply;
otherwise log as a follow-up.

### B4 — Surface bad `trip.timezone`

`trip_tz` silently falls back to `"UTC"` when missing/invalid (`smart_ripple.py:63`),
which makes the cross-midnight check use UTC midnight instead of local. Log a `WARNING`
when `trip.timezone` is unset/invalid so corrupt trip data is visible in observability.

### B5 — Optional: serialize concurrent ripples

Two concurrent ripples on the same trip can interleave reads/writes. Add a
`SELECT ... FOR UPDATE` on the trip row (or a trip-scoped advisory lock) so they
serialize. Lower priority; include if the scale-hardening work (RM-046) already favors it.

---

## Part C — Test Coverage (the biggest gap)

Today only `_apply_shift` / `_event_to_route_point` (unit) and the **legacy** engine
integration tests are covered. `SmartRippleEngine.shift_itinerary` cascade has **no**
integration coverage. Add tests with a **mocked `maps_service.directions`**:

**Existing coverage to keep green:**

- `tests/unit/test_smart_ripple.py` — 32 unit tests
- `tests/integration/test_intg_ripple_engine.py` — legacy engine
- `tests/integration/test_intg_ripple_api.py` — REST endpoint
- `tests/unit/test_concierge_executor.py` — 5 ripple-related tests

**New tests to add:**

*Smart Ripple cascade (service level):*

- Single-anchor shift; multi-event cascade with travel time exceeding gap.
- Gap-stop: a roomy gap halts propagation.
- `start_from_event_id` path; locked events as read-only waypoints (A9 regression).
- Cascade breaks at day boundary (B1 regression).
- CrossMidnightShiftError carries `shifted_so_far`; session left clean for caller (A3).
- EventNotEligibleError when anchor is locked/skipped/untimed (A4 regression).
- Maps API retry: first 2 calls fail, 3rd succeeds → correct travel time used (A10).
- Maps API all 3 fail → `0` fallback, cascade stops after anchor (A10).
- Timezone-aware cascade (IST trip) and a DST-boundary date.

*Concierge executor (service level):*

- `_move()` ripple: time change cascades downstream events (A7).
- `_move()` cross-day rejection returns error message (A7).
- `_add()` ripple: new event cascades downstream (A8).
- `_add_nearby()` anchor fix: inserted place pushes next event (A1 regression).
- CrossMidnightShiftError in `_shift()` / `_move()` / `_add()` → partial commit + warning message (A3).

*API endpoint:*

- CrossMidnightShiftError → 422 end-to-end and **no events persisted** (A3 regression).
- Authorization parity: non-editor blocked on REST and all Concierge ripple intents (A2).

---

## Out of Scope (per decisions)

- Rigid "shift-all by delta" policy — keeping elastic compression as-is.
- Overnight / cross-day cascades; transport modes beyond driving.
- Cross-day moves via Concierge — block with a message; user drags on timeline.
- Hard `delete_event` Concierge intent — `skip_event` is sufficient.
- Backward compaction pass when events are skipped (events only shift forward).
- Auto-ripple on raw REST API mutations (create/update/delete) — ripple stays
Concierge-only + manual REST. (Document this as intentional in the engine docstring.)

---

## Files to Modify


| File                                              | Changes                                                                                                                                                                                                              |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/app/services/smart_ripple.py`            | A3 (`shifted_so_far` on exception, no internal commit/rollback), A9 (locked waypoints), A10 (retry), B1 (day scoping), B2 (travel reuse/timeout/memo), B3 (departure_time opt.), B4 (tz warning), B5 (optional lock) |
| `backend/app/services/concierge_executor.py`      | A1 (anchor fix), A2 (auth gate), A3/A7/A8 (ripple for `_move`/`_add`, CrossMidnight catch), A4 (eligibility message), A6 (docstring)                                                                                 |
| `backend/app/api/endpoints/events.py`             | A2 (editor gate), A3 (rollback in endpoint catch), A5 (notification payload)                                                                                                                                         |
| Roles/deps module (`require_trip_admin` location) | A2 — add `require_trip_editor`                                                                                                                                                                                       |
| `backend/app/services/google_maps.py`             | Only if B3/B2 needs a signature change                                                                                                                                                                               |
| `backend/tests/`                                  | All Part C tests                                                                                                                                                                                                     |


---

## Verification

1. **Targeted tests:**
  ```
   cd backend && pytest tests/ -k "ripple or smart_ripple or find_nearby or concierge" -q
  ```
   All new + existing ripple/concierge tests green.
2. **Full suite:**
  ```
   cd backend && pytest -q
  ```
   Confirm no regressions across the ~480 tests.
3. **Manual A1 (`find_nearby` fix):** with two tightly-spaced events far apart
  geographically, add a nearby place via concierge and confirm the later event is pushed
   (it is currently not). Use the `debug-db` skill to inspect `start_time`s before/after.
4. **Manual A7 (`_move()` ripple):** move an event earlier in the Concierge chat; confirm
  downstream events cascade correctly via `debug-db`.
5. **Manual A3 (partial shift + warn):** fire a large "shift my day" that would push the
  last event past midnight; confirm the Concierge returns a partial-success message with
   N shifted events, and the last event is untouched.
6. **Manual A3 (REST 422):** fire the REST ripple endpoint with a large enough delta to
  cross midnight; confirm 422 with structured detail and that re-fetching the trip shows
   no partial shifts persisted.
7. **Auth parity (A2):** as a non-editor trip member, attempt the REST ripple (expect
  block) and the Concierge "shift my day" intent (expect the same outcome).

