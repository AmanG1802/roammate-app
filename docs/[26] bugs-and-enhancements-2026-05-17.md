# Bugs & Enhancements Implementation Plan — 2026-05-17

## Context

Six items reported against the production-launch-ready build (`ea56cc9 Ready for production launch`): three bugs that mishandle dates/times, and three UX/feature enhancements spanning iOS UI and the AI-chat entitlement model. They are scoped together because they collectively tighten the "first-30-minutes" user experience: a Plan-Trip user should land on a Trip that the widget recognizes as ongoing, with usage counted fairly and the planning conversation preserved.

Decisions confirmed with the user:
- **Bug 1**: Keep extracted start_date if present in the Plan-Trip prompt; otherwise default to today.
- **Bug 3**: Use the trip's stored timezone for promotion time conversion.
- **Plan→Brainstorm**: Buffer messages client-side during Plan Trip; backfill them into `BrainstormMessage` on trip create.
- **Usage**: Each Plan-Trip user message increments the brainstorm counter (same as Brainstorm chat).
- **Refresh button**: Move inline with the day badge in the top HStack row.

---

## Bug 1 — Widget shows past trip when Plan-Trip omits a date

### Root cause
- `POST /llm/plan-trip` returns `start_date: None` when the user's prompt has no date (`backend/app/services/llm/services/v1/roammate_v1.py:plan_trip` via `pre_processor._extract_dates`).
- `DashboardTripPlanner.tsx:90` / iOS `PlanTripStore.createTrip` forward `start_date: None` to `POST /trips/`.
- `create_trip` (`backend/app/api/endpoints/trips.py:65–114`) only auto-creates Day 1 when `start_date` is set, so the Trip has no `start_date`/`end_date`.
- Later, "Add Day from inside the trip" creates a `TripDay` with today's date (Day 1 gets current date), but `Trip.start_date` is still `NULL` — so the widget classifier in `dashboard.py:_classify` and iOS `TodayWidget.activeTrip()` can't see it as active, and `TodayWidgetCards.PostTripCard` ends up rendering "0 days passed".

### Fix
Default `start_date = today (in trip timezone)` at the Plan-Trip backend boundary, so all downstream behavior stays consistent.

- **`backend/app/api/endpoints/llm.py:plan_trip`** (lines 30–71): after computing `response`, if `response.start_date is None`, set it to `today_in_tz(request.timezone or "UTC").isoformat()` using `app.utils.tz.today_in_tz`.
- Accept `timezone` on `PlanTripRequest` (`backend/app/schemas/brainstorm.py:56–60`) — frontend already sends it on `TripCreate`; add it to the Plan request too.
- **`frontend/components/dashboard/DashboardTripPlanner.tsx`**: pass `Intl.DateTimeFormat().resolvedOptions().timeZone` in the plan-trip body.
- **`ios/Roammate/Network/PlanTripService.swift`** + `PlanTripStore.plan(...)`: send `TimeZone.current.identifier`.
- Do NOT change `create_trip`'s "no day if no start_date" behavior — by guaranteeing `start_date` at the Plan-Trip layer, Day 1 will always be auto-created.

### Verification
- Plan a trip with no date in the prompt → confirm `Trip.start_date == today` and `TripDay(day_number=1, date=today)` exists.
- Plan a trip with `"Goa next month"` → confirm extracted date is preserved.
- Open the iOS dashboard widget → trip appears as the active/ongoing card.

---

## Bug 2 — Editing trip date does not shift each Day's date

### Investigation
Backend `update_trip` (`backend/app/api/endpoints/trips.py:246–367`) **already** shifts every `TripDay.date` and every `TimelineItem.day_date` by the delta when `start_date` changes (lines 278–310). The bug is therefore on the client side or in a missing precondition.

Two likely causes — both should be checked and fixed:

1. **Missing `old_start`**: the shift only runs `if old_start and new_start != old_start` (line 282). After Bug 1 ships, all new Trips will have `start_date`, but **existing trips that were created without a start_date** still hit the `not old_start` branch — their `Trip.start_date` is updated (line 308) but `TripDay.date` rows are NOT touched. Add an `else` branch: when `old_start` is `None`, rebase every day from the new `start_date` using `day_number` (day 1 → new_start + 0d, day N → new_start + (N-1)d). Also rewrite each `TimelineItem.day_date` to match.

2. **iOS/web edit UI**: Explore agent reported no iOS UI for editing trip dates. Verify the path the user used (likely a web edit form or a TripSettings sheet) and confirm it actually calls `PATCH /trips/{id}` with a `start_date` field — not just `name`.

### Fix
- **`backend/app/api/endpoints/trips.py:update_trip`** — after the existing `if old_start and new_start != old_start:` block, add a branch for `old_start is None`:
  - Order existing days by `day_number`.
  - For each day, compute `target_date = new_start + timedelta(days=day_number - 1)`, update `TripDay.date`, then rewrite any `TimelineItem.day_date` row that referenced the old date.
  - Reuse the same forward/reverse-iteration trick as the existing shift code to avoid `UniqueConstraint("trip_id", "date")` collisions.
- Confirm the iOS/web "Edit dates" UI sends the `start_date` field on `TripUpdate`. If missing on iOS, add a simple sheet on `TripLandingView` that PATCHes the trip.

### Verification
- Create a trip without a date, add 3 days (each gets sequential today/today+1/today+2). Edit start_date to a future date → confirm all 3 `TripDay.date`s shift, day_numbers stay 1/2/3, and all events on those days move.
- Edit start_date on a normal trip (already had start_date) → confirm existing shift code still works (regression check).

---

## Bug 3 — Brainstorm → Idea Bin promotion uses UTC, displays +5:30 IST

### Root cause
`_time_category_to_times` in `backend/app/api/endpoints/brainstorm.py:36–48` builds the start/end datetimes with `today = datetime.now(dt_tz.utc).date()` and `tzinfo=dt_tz.utc`. For category `"midday"` (hour 12), it stores `12:00 UTC`. The iOS/web client renders this in the device timezone — IST clients see 17:30 (5:30 PM).

### Fix
Make the conversion trip-timezone-aware:

- **`backend/app/api/endpoints/brainstorm.py`**:
  - Change `_time_category_to_times(tc)` → `_time_category_to_times(tc, trip_tz: str | None)`.
  - Use `app.utils.tz.today_in_tz(trip_tz or "UTC")` for `today`.
  - Build the naive datetime with the time category hour, then call `app.utils.tz.to_utc(naive_dt, trip_tz)` to convert to UTC before storing (since `IdeaBinItem.start_time` is `DateTime(timezone=True)`).
- **`promote()`** (lines 297–377): fetch the trip's `timezone` field at the top of the loop and pass it into `_time_category_to_times`.

### Verification
- Create a brainstorm item with `time_category = "midday"` on a trip whose `timezone = "Asia/Kolkata"`.
- Promote → confirm the returned `start_time` (when rendered in IST) is `12:00 PM`, not `5:30 PM`.
- Repeat for a trip with `timezone = "America/Los_Angeles"` and confirm correct local rendering on web + iOS.

---

## Enhancement — Plan-Trip chat counts toward Brainstorm allowance & persists as first Brainstorm chat

### Scope
1. **Entitlement**: every user message sent to `POST /llm/plan-trip` increments `UsageCounter.brainstorm_messages` for free-tier users.
2. **Persistence**: client buffers the Plan-Trip turns (user + assistant). On successful `POST /trips/` (after preview accepted), backfill those turns into the new trip's `BrainstormMessage` table so the user sees them as the first chat when they open Brainstorm. Assistant turns render with markdown (Brainstorm chat already uses `ReactMarkdown` / iOS markdown renderer).

### Implementation

#### Backend
- **Surface `user_output` from Plan-Trip LLM** (precondition for persisting an assistant turn):
  - **`backend/app/services/llm/services/v1/prompts/plan_trip_v1.txt`** — expand the `user_output` spec so the LLM returns a user-friendly **markdown** brief (~120–220 words): one-line hook, **Highlights** bullet list (4–6 bold place names with reasons), optional **Pace** and **Best for** notes, friendly closing line. No day-by-day itinerary in `user_output` (that lives in `map_output`); no headings larger than `###`.
  - **`backend/app/services/llm/services/v1/roammate_v1.py:plan_trip`** — stop discarding `parsed.user_output`; include it in the returned dict.
  - **`backend/app/schemas/brainstorm.py:PlanTripResponse`** — add `user_output: str = ""`.
  - **`backend/app/api/endpoints/llm.py:plan_trip`** — forward `result["user_output"]` into the response.
  - The client buffers this string as the assistant turn's `content`; rendered as markdown in Brainstorm.
- **`backend/app/api/endpoints/llm.py:plan_trip`**:
  - Call `entitlements.enforce_brainstorm(user, db)` at the top (raises 402 if free-tier user is over quota).
  - After a successful LLM response, call `entitlements.bump_brainstorm_counter(user, db)` (mirroring `brainstorm.py:124–183` line 173).
- **`backend/app/api/endpoints/brainstorm.py`** — add a new endpoint `POST /trips/{trip_id}/brainstorm/messages/seed`:
  - Body: `{ messages: [{ role, content }] }`
  - Requires trip member; inserts the messages as `BrainstormMessage` rows tied to the trip + current user.
  - Idempotency: refuse if any `BrainstormMessage` already exists for this `(trip_id, user_id)` so accidental double-create doesn't duplicate.
- Schema additions in `backend/app/schemas/brainstorm.py`: `BrainstormSeedRequest`, `BrainstormSeedResponse`.

#### Frontend (Next.js)
- **`frontend/components/dashboard/DashboardTripPlanner.tsx`**:
  - Maintain a local `planMessages: { role, content }[]` array in component state; append every user prompt + assistant response.
  - Handle 402 from `/llm/plan-trip` → trigger the existing paywall modal (mirror `BrainstormChat.tsx` line 79).
  - After `POST /trips/` succeeds (line 90), call `POST /trips/{id}/brainstorm/messages/seed` with the buffered turns.

#### iOS
- **`ios/Roammate/Store/PlanTripStore.swift`**:
  - Already maintains `@Published var messages: [PlanTripMessage]` (line 3–7) — keep building it.
  - In `createTrip()` (after successful trip creation), call a new `BrainstormService.seedMessages(tripId:, messages:)`.
- **`ios/Roammate/Network/BrainstormService.swift`**: add `static func seedMessages(tripId: Int, messages: [(role: String, content: String)]) async throws`.
- **402 handling** in `PlanTripStore.plan()`: surface the paywall (mirror `BrainstormChatView` paywall handling).

### Markdown rendering
- Web Brainstorm already uses `ReactMarkdown` (`BrainstormChat.tsx:221`) — no change needed; seeded messages will render as markdown automatically.
- iOS `BrainstormChatView` should already handle markdown for assistant role; verify and add `Text(LocalizedStringKey(content))` or existing markdown view if missing.
- Plan-Trip assistant text comes from `PlanTripResponse.user_output` (the LLM's natural-language preview); store that string as the assistant `content` (it's already markdown-friendly).

### Verification
- Free-tier user with 0/15 used: send 3 messages in Plan Trip → counter shows 3/15. Trigger paywall by exhausting the quota mid-plan.
- Plan a trip → accept preview → trip created → open Brainstorm on that trip → see the Plan-Trip conversation as the first messages, assistant turns rendered as markdown.
- Abandon Plan Trip without creating → no `BrainstormMessage` rows, counter still reflects the attempted messages (correct — usage was consumed).
- Re-call seed endpoint on a trip that already has Brainstorm messages → returns idempotency error, no duplicates.

---

## Enhancement — iOS Notification Panel UX polish

File: `ios/Roammate/Views/Dashboard/DashboardView.swift` (`notificationBell` line 116, `notificationsOverlay` line 150).

### Issues
1. Shadow appears simultaneously with the dropdown — feels heavy and pops in.
2. Panel `.padding(.top, 50)` overlaps part of the bell icon depending on safe-area.
3. Full-screen scrim (`Color.black.opacity(0.3)`, line 152) dims the bell too — should remain "lit" above the scrim for a focused feel.

### Fix
- **Stagger the shadow**: split the panel transition. Render the panel surface without the shadow during the initial scale-in, then animate the shadow opacity from 0 → full over ~150ms after the panel finishes scaling. Implement via a second `@State` (e.g., `@State private var notifShadowVisible = false`) toggled inside an `.onAppear`/`.onChange(of: showNotifications)` with a short `withAnimation(.easeOut(duration: 0.18).delay(0.18))`. Apply `.shadow(...)` conditionally based on `notifShadowVisible`.
- **Reposition**: change `.padding(.top, 50)` (line 222) to anchor below the bell using a `GeometryReader` or a measured top offset (bell bottom + 8pt). Simplest: increase top padding to ~64pt and add `.padding(.trailing, RoammateSpacing.md)` so the panel's top-right corner sits just under the bell's lower-right, leaving the bell fully visible.
- **Bell stays lit above scrim**: re-render `notificationBell` (or a clone of it) above the scrim inside `notificationsOverlay`. Two approaches:
  - (Preferred) Use a `ZStack` ordering: scrim at bottom, then bell duplicate at top-right with the same frame/styling as the dashboard bell, then the panel. The duplicate bell sits on top of the scrim, so no dim. Make sure tapping it also closes the panel.
  - Alternative: use `.zIndex` on the real bell and exclude the scrim from covering it via a mask — more brittle.
- **"Richer" feel**: add a subtle `.blur(radius: 6)` to the scrim (system material-like) and a soft border highlight on the panel top edge. Add a 1pt hairline divider under the header that fades in with content.

### Verification
- Build & run iOS app → open dashboard → tap bell.
- Confirm: bell remains crisp (not dimmed), panel slides/scales in cleanly with shadow appearing slightly after, bell is not obscured by the panel.
- Tap outside → panel dismisses smoothly; reverse animation also staggers shadow first (fade out before panel scales away).

If layout tuning is non-trivial, invoke `/ui-ux-pro-max:ui-ux-pro-max` for an iteration pass once the structural changes are in.

---

## Enhancement — iOS Refresh Route button inline with day badge

File: `ios/Roammate/Views/Trips/Plan/PlanMapPage.swift` (`refreshRouteButton` line 283; current placement in overlay VStack lines 147–168).

### Fix
- Remove the dedicated `HStack { Spacer(); refreshRouteButton; Spacer() }` row at lines 160–166.
- Add `refreshRouteButton` into the existing top HStack that holds the day badge (around lines 150–158), placed after a `Spacer()` so the day badge stays leading and the refresh button sits trailing.
- Keep the existing styling (capsule, `.ultraThinMaterial`, color states). The capsule may need to be smaller to coexist with the day badge — reduce horizontal padding to 10 and font size to 10 if needed.
- The optional `contextMessage` (lines 327–342) currently renders directly under the button — move it into a separate row below the top HStack so it doesn't crowd the day badge.

### Verification
- Open a trip → Plan tab → Map page.
- Confirm refresh button sits in the top row next to the day badge, no longer floating mid-screen.
- Confirm stale/loading/error color states still trigger correctly, context message still appears (now in its own row).

---

## Critical files

Backend:
- `backend/app/api/endpoints/llm.py` — Bug 1, Plan-Trip entitlement
- `backend/app/api/endpoints/trips.py:246` — Bug 2 (`update_trip` rebase-from-null branch)
- `backend/app/api/endpoints/brainstorm.py:36`, `:297` — Bug 3, seed endpoint
- `backend/app/schemas/brainstorm.py` — add `BrainstormSeedRequest`, timezone on `PlanTripRequest`
- `backend/app/utils/tz.py` — reuse `today_in_tz`, `to_utc`
- `backend/app/services/entitlements.py:191`, `:208` — reuse `enforce_brainstorm`, `bump_brainstorm_counter`

Frontend (Next.js):
- `frontend/components/dashboard/DashboardTripPlanner.tsx` — buffer messages, send timezone, call seed endpoint, handle 402

iOS:
- `ios/Roammate/Views/Dashboard/DashboardView.swift:116,150` — notification panel polish
- `ios/Roammate/Views/Trips/Plan/PlanMapPage.swift:147,283` — refresh button move
- `ios/Roammate/Store/PlanTripStore.swift` — call seed on trip create, 402 handling
- `ios/Roammate/Network/PlanTripService.swift` — send timezone on plan request
- `ios/Roammate/Network/BrainstormService.swift` — add `seedMessages`

---

## Suggested execution order
1. Bug 3 (smallest blast radius, isolated to one function).
2. Bug 1 (single backend default + small client tweaks).
3. Bug 2 (backend branch + verify edit UI).
4. Plan-Trip → Brainstorm unification (cross-cutting; biggest change).
5. iOS Refresh button (pure SwiftUI tweak).
6. iOS Notification panel polish (SwiftUI, iterate with `/ui-ux-pro-max` if needed).
