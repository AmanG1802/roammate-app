# Smart Ripple Engine + Concierge — Unified Robustness & USP Plan

> Merges `docs/[48] smart-ripple-robustness.md` and `docs/[49] concierge-usp-reliability.md`
> into one sequenced plan. On approval this becomes the next `docs/[NN] …md` and supersedes
> [48]/[49]. (Note: [49] refers to the ripple plan as "[42]" — stale numbering; it means [48].)

## Context

Roammate's two on-trip systems are tightly coupled and currently unreliable:

- **Smart Ripple Engine** (`backend/app/services/smart_ripple.py`) — travel-time-aware
  re-scheduler. It has correctness bugs: Concierge `move`/`add`/`find_nearby` either bypass
  ripple or no-op it, locked events are dropped as route waypoints, a Maps failure silently
  truncates the cascade, error handling leaves a dirty session, and an auth gate exists on
  REST but not on the Concierge path. Cascade integration coverage is near zero.
- **Concierge** (`api/endpoints/concierge.py`, `services/concierge_executor.py`) — the on-trip
  AI assistant we want to make the product **USP**. Today it reasons with **fake travel
  times** and **today-only** context, is a **private per-user thread**, has no preview/undo,
  and no opening-hours awareness.

The user's directive: **fix the Smart Ripple bugs first**, then layer enhancements on both
services so they are reliable, robust, and feature-complete — shipped to **both web and iOS**.

### Decisions locked (this session)

- **Auth gate = admin-only.** There is no "editor" role (TripMember roles are
  `admin` / `view_with_vote` / `view_only`). We add a `require_trip_editor` helper that
  **currently aliases admin** so REST and Concierge enforce one consistent gate, and future
  broadening is a one-line change. Concierge **write/confirm = Plus AND admin**; **read = all
  trip members** (incl. non-Plus, an upsell surface).
- **In scope:** shared trip-wide chat, dry-run preview + validation, opening-hours awareness,
  undo last action, persona polish — all of [49]'s enhancements.
- **Opening + closing hours** are enriched across Brainstorm / Idea Bin / Timeline via the
  `PlaceColumnsMixin`, by every AI chat/workflow, **and honored by the Ripple Engine and
  Concierge** (feasibility warnings) — all **gated by one new feature flag**
  `GOOGLE_MAPS_FETCH_OPENING_HOURS` (sibling to `GOOGLE_MAPS_FETCH_PHOTOS`/`_RATING`). Flag off
  ⇒ no enrichment, no hours logic anywhere.
- **Ripple hardening:** **B1** (same-day scoping), **B2** (travel-time performance &
  resilience: DayRoute leg-reuse + per-call timeout + in-call memoization), **B4** (surface bad
  `trip.timezone`). **Deferred:** B3 departure-time, B5 concurrent-ripple lock.

### Out of scope / Future Scope

Documented as intentional follow-ups, not built now:

- **Overnight / cross-day cascade (Ripple R2):** let a late event push work past midnight onto
  the next `day_date` instead of erroring. Requires multi-day cascade math, the cross-midnight
  guard becoming a roll-forward, and UI for "spilled to tomorrow". v1 still rejects with
  `CrossMidnightShiftError`.
- **Transport modes beyond driving:** walking/transit/cycling durations in `directions()` and a
  per-trip or per-leg mode preference. v1 is driving-only.
- **Cross-day moves via Concierge:** today blocked with a message ("drag the event to the new
  day from the timeline"); future work would let chat move an event across days and re-ripple
  both the source and destination days.
- **Persona-tailored recommendations (3.4):** load trip members' `User.personas` and summarize
  a compact "group vibe" line into the prompt to bias `find_nearby`/suggestions. Deferred to a
  later polish pass.
- Also deferred: backward compaction (R3); rigid shift-all policy; hard delete intent;
  auto-ripple on raw REST CRUD; websocket realtime for shared chat (refetch model only); ripple
  B3/B5 above.

---

## Phase 0 — Shared foundations (small, unblocks everything)

- **Roles** (`backend/app/services/roles.py`): add `require_trip_editor(db, trip_id, user_id)`
  aliasing `require_trip_admin` for v1, with a comment that it's the single edit gate.
- **Docstrings** (A6 / B-3): fix the "UTC-aware TIMESTAMPTZ" lies in
  `concierge_executor.py` header and any sibling, reflecting the DATE/TIME split.

---

## Phase 1 — Smart Ripple correctness bugs (DO FIRST)

All in `smart_ripple.py`, `concierge_executor.py`, `events.py`. Reuse existing
`combine_in_tz`/`split_in_tz` (`app/utils/tz.py`) and `_apply_shift`/`_event_to_route_point`.

- **A2 — Auth parity.** Apply `require_trip_editor` to `POST /events/ripple/{trip_id}`
  (`events.py:335`, replacing `require_trip_admin`) **and** to Concierge write intents.
- **A3 — Caller-controlled commit/rollback.** `shift_itinerary` must **not** internally
  `commit()`/`rollback()` on `CrossMidnightShiftError`; instead attach
  `shifted_so_far: list[Event]` to the exception and re-raise (the failing event is unmutated
  — see `_apply_shift` raising before mutation). Then:
  - REST `events.py` catch → `await db.rollback()` → existing 422 structured detail.
  - Concierge methods catch → `await db.commit()` → partial-success message using
    `error.shifted_so_far` ("Shifted N events — [Event] would run past midnight, so I stopped
    there.").
  - **Move the lone `await db.commit()` at `smart_ripple.py:145` out** into the success path
    only after the loop completes without raising (still inside the engine for the non-dry,
    REST-rollback-friendly contract — REST wraps in try/except and rolls back).
- **A1 — `find_nearby` ripple no-op.** In `_add_nearby` (`concierge_executor.py:351`) anchor
  on the inserted event: `shift_itinerary(..., delta_minutes=0, start_from_event_id=event.id)`.
  Filter the unchanged anchor out of the returned `shifted` list when `delta==0` and its time
  didn't change.
- **A4 — `start_from_event_id` silent no-op.** When the target is locked/skipped/untimed/
  wrong-trip, look it up **unfiltered** and raise a typed `EventNotEligibleError(reason)` the
  Concierge surfaces ("That event is locked — unlock it to shift from there", etc.) instead of
  returning `[]` → misleading "No events needed shifting".
- **A7 — `_move()` triggers ripple.** Add `user_id` to `_move` signature; reject cross-day
  (`new_day_date != event.day_date` → message to drag on timeline); after committing the time
  change call `shift_itinerary(delta_minutes=0, start_from_event_id=event.id, user_id=...)`;
  return moved-event ∪ ripple-shifted; A3 CrossMidnight catch.
- **A8 — `_add()` triggers ripple.** Add `user_id`; after commit, if `start_time` set, call
  `shift_itinerary(delta_minutes=0, start_from_event_id=event.id, user_id=...)` (same as fixed
  `_add_nearby`); A3 catch. Update `execute()` dispatch to pass `user_id` into `_move`/`_add`.
- **A9 — Locked events as read-only waypoints.** Remove `Event.is_locked == False` from the
  query (`smart_ripple.py:72`); in the loop, if `curr.is_locked` skip `_apply_shift` but keep
  its `ends_utc` populated so the next leg measures travel **from** the locked venue; locked
  events are never mutated but always counted as waypoints.
- **A10 — Maps failure truncates cascade.** In `_get_travel_minutes`, retry **3×** with
  exponential backoff (100/200/400 ms) before the existing `return 0` fallback; on final
  failure log a structured warning (leg event ids + trip id). Note: `directions()` already has
  caching + a circuit breaker, so the retry only re-attempts transient app-level failures.
- **A5 — Notification payload.** In `events.py` rename `delta_minutes` →
  `requested_delta_minutes` in the `RIPPLE_FIRED` payload; keep `shifted_count`.

---

## Phase 2 — Smart Ripple hardening (minimal) + new functionality

- **B1 — Explicit same-day scoping.** After choosing the anchor, `break` the cascade when
  `curr.day_date != anchor.day_date` (today this only holds by accident via the overnight gap).
- **B2 — Travel-time performance & resilience** (matters at 50k scale, RM-046). Today
  `shift_itinerary` issues up to N sequential blocking `directions()` calls inside the request.
  - **Reuse stored `DayRoute` legs** when the day's `waypoint_fingerprint` is unchanged: the
    legs already carry per-edge `from_event_id`/`to_event_id`/`duration_s`
    (`schemas/route.py` `RouteLeg`), so a fresh-fingerprint lookup avoids re-calling Directions.
    Recompute the fingerprint via the existing `compute_waypoint_fingerprint`
    (`api/endpoints/maps.py:70`).
  - **Bound each call** with `asyncio.wait_for(...)`; on timeout fall back to the stored leg,
    else `0` (A10 retry still applies to live calls).
  - **Memoize within a call** by `(origin_key, dest_key)` so repeated legs aren't recomputed.
- **B4 — Surface bad `trip.timezone`.** Log a `WARNING` when `trip.timezone` is unset/invalid
  before the `"UTC"` fallback (`smart_ripple.py:63`).
- **R1 — Dry-run mode.** `shift_itinerary(..., dry_run: bool = False)`: compute the full
  cascade in-memory and return a structured result —
  `projected: [(event_id, new_start, new_end)]` + `warnings` (overlap, cross-midnight,
  opening-hours) — **without** committing (works inside the caller's `SAVEPOINT`). Builds on
  A3's no-internal-commit refactor. (Suggest a small `RippleResult` dataclass; non-dry callers
  keep the `list[Event]` return or read `.shifted`.)
- **R4 — Honor opening/closing hours** (gated by `GOOGLE_MAPS_FETCH_OPENING_HOURS`). During the
  cascade, when the flag is on and an event has `opening_hours`, check the (possibly shifted)
  projected window against **both open and close** times via the Phase 3 `is_open_during`
  helper; append a structured opening-hours warning to the result (e.g. "Louvre closes 6:00pm —
  this lands 6:40–8:10pm"). **Warn-and-allow** — detection only, never blocks or reorders. Flag
  off ⇒ this check is skipped entirely. Depends on Phase 3.

---

## Phase 3 — Opening/closing-hours enrichment (foundational for R4 & 3.7)

Make hours a first-class enriched field everywhere, gated by a flag.

- **Flag** (`backend/app/core/config.py`): add `GOOGLE_MAPS_FETCH_OPENING_HOURS: bool = True`
  next to `_FETCH_PHOTOS`/`_RATING`. Mirror in `.env.example`, `docker-compose.yml`, any
  Railway/Vercel env docs, and set `= False` in `admin_costs.py`'s flag-disabling block.
  *(User named this `USE_OPEN_HOURS`; using the `GOOGLE_MAPS_FETCH_*` prefix for consistency
  with its two siblings — rename if you prefer the shorter form.)*
- **Model** (`backend/app/models/all_models.py`): add `opening_hours = Column(JSON, nullable=True)`
  to `PlaceColumnsMixin` (covers BrainstormBinItem, IdeaBinItem, TimelineItem) and append
  `"opening_hours"` to the `PLACE_FIELDS` tuple — this single addition makes it propagate
  through every workflow that copies via `PLACE_FIELDS` (brainstorm.py, maps.py, tutorial_seed,
  concierge). Store the Places `regularOpeningHours` JSON (has both open **and** close periods).
- **Field mask + mapping** (`google_maps/v1.py`, `v2.py`, `mock.py`): in
  `_build_details_field_mask` add `regularOpeningHours` when the flag is on; in the details/
  nearby response mappers set `item["opening_hours"] = details.get("regularOpeningHours")`
  guarded by the flag — same shape as the existing photo/rating blocks (e.g. `v2.py:324-336`,
  `v2.py:444-451`). `mock.py` returns a deterministic fixture when the flag is on.
- **Migration** (Alembic): add nullable `opening_hours` JSON to `brainstorm_bin_item`,
  `idea_bin_item`, `timeline_item`.
- **Hours util**: small helper `is_open_during(opening_hours, day_date, start, end) -> bool|None`
  (None = unknown hours) used by R4 and the validators.

---

## Phase 4 — Concierge correctness + real context

- **B-4 — `enforce_concierge` parity.** `/execute` (`concierge.py:256`) must pass `trip=trip`
  like `/chat` does.
- **B-5 — `_move` drops time when `start_time` null.** Either apply the new time (set
  start/end from params) or return a clear message — no silent drop (`concierge_executor.py:209`).
- **3.2 / B-1 — Real travel times in prompt.** Replace `_build_travel_times`'s
  `"(will be computed on demand)"` (`concierge.py:120-127`) with real per-leg minutes via the
  cached `directions()` for consecutive active events. (No B2; cache + breaker already make
  this cheap.) Foundational for the validators.
- **3.3 / B-2 — Whole-trip multi-day context.** Replace `_load_today_events` usage in `/chat`
  with a whole-trip loader grouped by day headers (`Day 3 — 2026-06-13`), each event tagged
  `[id=…]`, capped to a token budget (near days full, distant days summarized). Keep the
  data-query endpoints (whats-next/today-summary) today-scoped.
- **Prompt** (`concierge_dispatch_v1.txt` or a v2): add multi-day context, real travel-time,
  and opening-hours guidance.

---

## Phase 5 — Shared, trip-wide Concierge chat (3.1)

One conversation per trip, visible to the whole group.

- **History scoping** (`concierge.py`): `_load_history` and the action-card lifecycle drop the
  `user_id` filter — scope by `trip_id` only. Keep `ConciergeMessage.user_id` as **author**.
  Interleave author name/id into the LLM history so the model knows who said what.
- **Access** : posting/proposing/confirming requires **Plus AND admin** (`require_trip_editor`
  + `enforce_concierge`); a single pending action_card is confirmed once by any eligible
  member. **All members read** (gate posting, not reading) — add/relax a read endpoint.
- **Schemas** (`schemas/concierge.py`): add author fields (id, name) to message responses.
- **Frontend** (web `ConciergeChatDrawer.tsx`; iOS `ConciergeStore.swift`,
  `TripConciergeView.swift`, `ConciergeCards.swift`, `Models/Concierge.swift`): author labels
  ("Aman:"), read-only state for non-Plus/non-admin, refetch thread on open/after send.

---

## Phase 6 — Dry-run preview + feasibility validation (3.5 / 3.6)

- **Dispatch preview** (`concierge.py` `/chat`, `concierge_executor.py`): for
  `shift_timeline`/`move_event`/`add_event`/`find_nearby`, open `db.begin_nested()`
  (SAVEPOINT), apply the would-be mutation, call `shift_itinerary(..., dry_run=True)`, capture
  projected `[(event_id, new_start, new_end)]` + warnings, then **roll back the savepoint**
  (nothing persists at dispatch).
- **Validation (warn-and-allow, never block)**: surface warnings — time overlaps,
  travel-infeasible gaps (gap < real travel), cross-midnight, opening-hours (Phase 7).
- **Schema** (`schemas/concierge.py`): new `preview` field on `ConciergeChatResponse` carrying
  a structured impact payload — a summary line, a per-event `changes` list
  (`{event_id, title, old_start, new_start, old_end, new_end}`), and a `warnings` list
  (`{kind: overlap|travel|cross_midnight|opening_hours, message, event_id}`).
- **`/execute`** re-runs the same mutation for real (committed) — the Phase 1 executors already
  do this.
- **Frontend — rich preview UI in the chat window** (web `ConciergeChatDrawer.tsx` /
  `ConciergeActionBar.tsx`, iOS `ConciergeCards.swift`): the action card renders a real,
  scannable impact view, not a one-liner —
  - a **before → after timeline diff**: each affected event as a row with old time struck
    through and new time highlighted (e.g. `Dinner  7:30 → 8:40pm`), color-coded by direction
    of shift;
  - a **summary header** ("Shifts 3 events, +40 min total");
  - **warning chips/rows** for each feasibility issue (⚠ travel-infeasible, 🌙 cross-midnight,
    🕗 opening-hours "Louvre closes 6pm") — visually distinct, non-blocking;
  - **Confirm / Cancel** actions; Confirm calls `/execute`. Follow the design-system tokens
    (`frontend-theme` skill) and ship the SwiftUI-native equivalent on iOS.

---

## Phase 7 — Opening/closing-hours awareness in Concierge (3.7)

- Gated by `GOOGLE_MAPS_FETCH_OPENING_HOURS`. The dry-run ripple (R4) flags any event whose
  projected window falls outside its venue's `opening_hours` — respecting **both open and
  close** (Phase 3 data + `is_open_during`); the warning rides in `preview.warnings` and renders
  as a 🕗 chip in the action card. Also feed each event's open/close into the **prompt context**
  (Phase 4) so the LLM avoids proposing visits outside hours in the first place. Detection +
  guidance only — confirm still allowed (warn-and-allow). Flag off ⇒ no hours context, no
  warnings.

---

## Phase 8 — Undo last action (3.8)

- **Model + migration**: new `ConciergeAction` table (`trip_id`, `user_id`, `intent`,
  `inverse_patch` JSON, `created_at`, `undone_at`).
- **Capture** (`concierge_executor.py`): on every successful `/execute`, record an
  `inverse_patch` of prior state for **every** touched event (anchor + all ripple-shifted):
  prior `(day_date, start_time, end_time, is_skipped)`; for adds → inserted event id (inverse =
  delete); for skips → prior flag.
- **Endpoint** (`concierge.py`): `POST /{trip_id}/undo` reverts the most recent
  not-yet-undone action (any eligible admin), applies the inverse patch, sets `undone_at`,
  emits a system message + notification. Second undo = no-op.
- **Frontend**: "Undo" affordance on the last action card, web + iOS.

---

---

## Tests (throughout — biggest existing gap is ripple cascade coverage)

Keep green: `tests/unit/test_smart_ripple.py`, `tests/integration/test_intg_ripple_engine.py`,
`test_intg_ripple_api.py`, `tests/unit/test_concierge_executor.py`.

**Smart Ripple (service, mocked `maps_service.directions`)**: single + multi-event cascade;
gap-stop; `start_from_event_id`; **locked events as read-only waypoints (A9)**; **day-boundary
break (B1)**; **CrossMidnight carries `shifted_so_far`, session clean (A3)**;
**EventNotEligibleError (A4)**; **Maps retry 2-fail-then-succeed / all-3-fail → 0 fallback
(A10)**; IST + DST cascade; **dry_run returns projected + warnings, nothing persists (R1)**;
**opening-hours warning (R4)**.

**Concierge executor**: `_move` ripple + cross-day rejection (A7); `_add` ripple (A8);
`_add_nearby` anchor fix (A1); CrossMidnight partial-commit messages (A3); preview
savepoint-rollback (3.5); undo restores every touched event + second-undo no-op (3.8); B-5 move
time-set.

**Endpoint/access**: REST CrossMidnight → 422 + nothing persisted (A3); auth parity non-admin
blocked on REST and all Concierge write intents (A2); shared-history visible across members,
non-Plus read-only (3.1); enrichment writes `opening_hours` with flag on / skips with flag off.

---

## Files to modify

| File | Phases |
|------|--------|
| `backend/app/services/roles.py` | 0 (`require_trip_editor`) |
| `backend/app/services/smart_ripple.py` | 1 (A3/A4/A9/A10), 2 (B1/B4/R1/R4) |
| `backend/app/services/concierge_executor.py` | 1 (A1/A3/A4/A7/A8), 4 (B-5), 6 (preview/SAVEPOINT), 7, 8 (inverse_patch/undo), docstring |
| `backend/app/api/endpoints/events.py` | 1 (A2/A3/A5) |
| `backend/app/api/endpoints/concierge.py` | 4 (B-4/travel/multi-day), 5 (shared history+access), 6 (preview), 8 (`/undo`) |
| `backend/app/schemas/concierge.py` | 5 (author), 6 (preview/warnings), 8 (undo) |
| `backend/app/models/all_models.py` | 3 (`opening_hours` on mixin + `PLACE_FIELDS`), 8 (`ConciergeAction`) |
| `backend/app/core/config.py` + `.env.example` + `docker-compose.yml` + `admin_costs.py` | 3 (flag) |
| `backend/app/services/google_maps/{v1,v2,mock}.py` | 3 (field mask + mapping) |
| `backend/.../prompts/concierge_dispatch_v1.txt` | 4, 7 |
| Alembic migrations | 3 (`opening_hours` ×3 tables), 8 (`ConciergeAction`) |
| Web `ConciergeChatDrawer.tsx`, `ConciergeActionBar.tsx` | 5/6/7/8 |
| iOS `ConciergeStore.swift`, `TripConciergeView.swift`, `ConciergeCards.swift`, `Models/Concierge.swift` | 5/6/7/8 |
| `backend/tests/` | all phases |

---

## Verification

1. **Targeted backend tests**
   `cd backend && pytest tests/ -k "ripple or smart_ripple or find_nearby or concierge or preview or undo or opening" -q`
2. **Full suite**: `cd backend && pytest -q` — no regressions across ~480 tests.
3. **A1 manual**: two tightly-spaced far-apart events → add nearby via concierge → later event
   is pushed (`debug-db` before/after).
4. **A7 manual**: move an event earlier in chat → downstream cascades (`debug-db`).
5. **A3 manual**: big "shift my day" past midnight → Concierge partial-success message, last
   event untouched; same via REST → 422 + nothing persisted on refetch.
6. **Preview (3.5)**: "push everything 45 min" → card shows true projected times; pre-confirm
   refetch shows **nothing persisted** (savepoint); confirm → `debug-db` shows committed shift.
7. **Opening hours (3.7)**: add/move past venue close → card shows ⚠ but allows confirm; toggle
   `GOOGLE_MAPS_FETCH_OPENING_HOURS=False` → enrichment + warnings disappear.
8. **Undo (3.8)**: cascade several events → Undo → all return to prior times; second Undo no-op.
9. **Shared thread (3.1)**: member B (Plus admin) sees member A's messages/actions with author
   labels in one thread; non-Plus member is read-only.
