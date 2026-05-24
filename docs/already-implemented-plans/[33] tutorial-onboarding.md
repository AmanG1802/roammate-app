# [33] Tutorial Onboarding — Guided NYC Tour

## Context

First-time users land on a multi-surface app (Dashboard, Trip Detail, Timeline, Brainstorm Chat & Bin, Idea Bin, Map, Concierge) with no scaffolded introduction. Persona and Plus onboarding modals fire immediately on first login but never explain the product itself, and Concierge — a key Plus differentiator — is paywalled before users can experience its value.

We will add a skippable, spotlight-based guided tour anchored to a seeded **"Welcome to Roammate — New York"** trip. The tour runs once per platform (iOS and Web are independent), is replayable from Settings, gates the persona/paywall popups until completed or skipped, and gives the user a free, fully-canned taste of Concierge — without consuming free-tier quota or making any LLM/Maps API calls.

---

## Decisions (from clarifying questions)

| Topic | Decision |
|---|---|
| Trip provisioning | **Lazy** — created when tutorial first starts (or replayed from Settings). |
| Scope | **8 steps**: Dashboard → Plan trip via AI Chat → Trip overview → Timeline → Brainstorm Chat → Brainstorm Bin → Idea Bin → Move-to-Timeline + Map/Refresh Route → Concierge → back to Dashboard with delete prompt. |
| Interaction | **Hybrid spotlight** — dim + highlight target, Prev/Next/Skip; specific steps include a scripted "Try it" action. |
| State | **Backend flag**, replayable, **per-platform** (no iOS↔Web sync). |
| First trigger | **Auto on first login** via welcome modal; replayable from Settings. |
| AI-chat step | **Separate trip-creation AI planner** surface, shown as a step before trip overview. |
| Mock data | **Seeded + limited "Try it" actions**, canned LLM/Maps responses, no real API calls. |
| Concierge unlock | **Per-trip override** via `Trip.is_tutorial` flag. |
| Resume | Persist `tutorial_step` — resume where left off. |
| Trip visibility | Inline like a regular trip during tutorial. After completion, trip becomes read-only: no new brainstorm chat, no Concierge calls, no edits — only the canned content remains viewable until deleted. |
| Delete prompt | Separate confirmation modal after the final tour step. |

---

## Architecture Overview

### Backend
- New `Trip.is_tutorial: bool` column. Single source of truth for all gates/bypasses.
- New `User.tutorial_status_ios` and `User.tutorial_status_web` enums (`not_started | in_progress | completed | skipped`) + `tutorial_step_ios` / `tutorial_step_web` int columns.
- New endpoint group `/api/tutorial/*` to start, advance, complete, skip, replay, and delete the tutorial trip.
- All quota gates (`entitlements.enforce_active_trip`, `enforce_brainstorm`, `enforce_concierge`, `bump_brainstorm_counter`) skip when `trip.is_tutorial is True`.
- Brainstorm chat, Concierge chat, Maps route, and Idea-Bin enrichment short-circuit to **canned fixtures** when `trip.is_tutorial`.
- Once `Trip.is_tutorial_completed` is true, write paths (chat send, concierge send, event edits) return 423 / `tutorial_locked` — read paths still work.

### Frontend (Web + iOS)
- Tutorial driver state machine lives client-side, but `tutorial_status` and `tutorial_step` are synced to backend on every advance for resume.
- Spotlight overlay component (custom; Framer Motion on Web, SwiftUI mask + spring on iOS) with Prev / Next / Skip / "Try it" buttons.
- Persona + Plus onboarding modals on the Dashboard are gated behind `tutorial_status in {completed, skipped}` for the current platform.

---

## 1. Backend Changes

### 1.1 Schema
- New migration `006_add_tutorial.sql` (raw SQL, following `migrations/` numbering convention):
  - `ALTER TABLE trips ADD COLUMN is_tutorial BOOLEAN NOT NULL DEFAULT FALSE;`
  - `ALTER TABLE trips ADD COLUMN is_tutorial_completed BOOLEAN NOT NULL DEFAULT FALSE;`
  - `ALTER TABLE users ADD COLUMN tutorial_status_web VARCHAR(20) NOT NULL DEFAULT 'not_started';`
  - `ALTER TABLE users ADD COLUMN tutorial_status_ios VARCHAR(20) NOT NULL DEFAULT 'not_started';`
  - `ALTER TABLE users ADD COLUMN tutorial_step_web INT NOT NULL DEFAULT 0;`
  - `ALTER TABLE users ADD COLUMN tutorial_step_ios INT NOT NULL DEFAULT 0;`
  - `CREATE UNIQUE INDEX uq_user_tutorial_trip ON trips(created_by_id) WHERE is_tutorial = TRUE;` (one tutorial trip per user at a time).

### 1.2 Model updates
- `backend/app/models/all_models.py`:
  - Add `is_tutorial`, `is_tutorial_completed` to `Trip`.
  - Add 4 columns to `User`.

### 1.3 Entitlement bypass (single chokepoint)
- `backend/app/services/entitlements.py`:
  - `enforce_active_trip(db, user, *, is_tutorial=False)` — early-return when `is_tutorial`.
  - `enforce_brainstorm(db, user, *, trip)` — early-return when `trip.is_tutorial`.
  - `enforce_concierge(db, user, *, trip)` — early-return when `trip.is_tutorial` (this is the Concierge unlock).
  - `bump_brainstorm_counter(db, user, *, trip)` — no-op when `trip.is_tutorial`.

### 1.4 Tutorial seed fixtures
- New module `backend/app/services/tutorial_seed.py`:
  - `seed_tutorial_trip(db, user) -> Trip`: idempotent. Creates a 3-day NYC trip (today through today+2 in user TZ), with:
    - 3 `TripDay` rows.
    - ~5 prebuilt `Event` rows across the days (Times Square, Central Park picnic, MoMA, Brooklyn Bridge sunset, Joe's Pizza), each with `lat/lng/place_id` already set so no Maps lookup is needed.
    - 4 `IdeaBinItem` rows (e.g., High Line, Statue of Liberty, Top of the Rock, Katz's Deli).
    - 6 `BrainstormBinItem` rows (subset of canned candidates).
    - 8 `BrainstormMessage` rows (4 user + 4 assistant) forming a coherent canned conversation.
    - 3 `DayRoute` rows with pre-computed polylines + leg fixtures (stored verbatim, never recomputed).
    - 2 `ConciergeMessage` rows (1 user + 1 assistant) seeding a friendly intro chat.
  - Fixture content lives in `backend/app/services/tutorial_fixtures.py` as Python constants (polylines, place IDs, photo URLs from existing real NYC data, frozen at write-time).

### 1.5 Canned short-circuits
- `backend/app/api/endpoints/brainstorm.py` (chat handler): if `trip.is_tutorial`, return one of N canned assistant replies (round-robin from fixture list keyed by current message count); skip LLM call entirely. If `trip.is_tutorial_completed`, return 423.
- `backend/app/api/endpoints/concierge.py` (chat + execute): same pattern, return canned responses; bypass `enforce_concierge` when tutorial.
- `backend/app/api/endpoints/maps.py` (`POST /{trip_id}/route`): if `trip.is_tutorial`, load the existing `DayRoute` row and return it as the route response without calling `google_maps_service.directions()`.
- `backend/app/api/endpoints/idea_bin.py` (add item / promote to timeline): if `trip.is_tutorial`, skip `find_place` enrichment — fixtures already include all place metadata.

### 1.6 New endpoints
New router `backend/app/api/endpoints/tutorial.py`:
- `GET  /api/tutorial/status` → `{ status, step, trip_id | null, platform }` (platform derived from `X-Client-Platform` header, defaults to `web`).
- `POST /api/tutorial/start` → creates (or returns existing) tutorial trip, sets `status=in_progress`, `step=1`.
- `PATCH /api/tutorial/step` → `{ step: int }` updates current step (for resume).
- `POST /api/tutorial/skip` → sets `status=skipped`. Tutorial trip kept (user can finish later) but tour overlay stops.
- `POST /api/tutorial/complete` → sets `status=completed` and `Trip.is_tutorial_completed=True` (locks the trip).
- `POST /api/tutorial/replay` → re-seeds a fresh tutorial trip (deletes any existing one for that user), resets status to `in_progress`, step=1.
- `DELETE /api/tutorial/trip` → removes the seeded trip (final cleanup CTA).

### 1.7 Trip-list & trip-read endpoints
- `GET /api/trips/` already returns all owned trips; tutorial trip shows up inline. Include `is_tutorial` and `is_tutorial_completed` in the Trip schema so the frontend can badge/lock the UI.

### 1.8 Tests
- `backend/tests/cross/test_tutorial_flow.py`:
  - Start → status updates → canned brainstorm reply → canned concierge reply → canned route → complete → write-locked → replay → delete.
  - Assert no LLM client and no `google_maps_service` methods are called (use `MagicMock` asserts).
  - Assert free-tier counters do not increment.
- Extend `backend/tests/api/test_brainstorm_api.py` and existing entitlement tests to cover the `trip.is_tutorial` bypass.

---

## 2. Web Frontend Changes (Next.js)

Reference theme: existing Tailwind palette in `frontend/tailwind.config.ts` (indigo-600 primary, slate ink, Inter, Framer Motion). Reference design conventions from `/frontend-theme` skill and `/ui-ux-pro-max:ui-ux-pro-max` (spotlight overlay, minimal modal, accessible focus management).

### 2.1 Tutorial state hook
- New `frontend/hooks/useTutorial.ts`:
  - TanStack Query for `GET /api/tutorial/status` (key: `['tutorial','web']`).
  - Mutations: `start`, `advance(step)`, `skip`, `complete`, `replay`, `deleteTutorialTrip`.
  - Helpers: `isTutorialActive`, `currentStep`, `tutorialTripId`.

### 2.2 Tutorial driver
- New `frontend/components/tutorial/TutorialProvider.tsx`:
  - Wraps the app at `app/layout.tsx` (inside `ProtectedRoute` scope).
  - Holds the canonical 8-step script (target selector, route, copy, "Try it" handler).
  - Handles route changes via `next/navigation` (push to `/trips/{id}`, `/trips/{id}?view=plan`, etc. as required by the step).
- New `frontend/components/tutorial/SpotlightOverlay.tsx`:
  - Renders a full-screen `motion.div` backdrop with an SVG cutout aligned to the target element's bounding rect (resized on scroll/resize via `ResizeObserver`).
  - Floating popover anchored next to the spotlight: title, body, optional "Try it" button, Prev / Next / Skip footer, step indicator (e.g. "3 / 8").
  - Uses Framer Motion `AnimatePresence` for enter/exit; matches existing modal motion tokens.
- New `frontend/components/tutorial/WelcomeModal.tsx`:
  - First-launch modal with "Start tour" / "Skip for now".
  - Reuses existing modal scaffolding (same shell as `OnboardingPersonaModal`).

### 2.3 Step script (web)
Each step targets a stable DOM anchor. We add `data-tutorial="<id>"` attributes (lightweight, design-token-free) to:

| # | Surface | Target (`data-tutorial`) | Copy seed | Try it |
|---|---|---|---|---|
| 1 | Dashboard | `dashboard-trips-grid` + `new-trip-btn` | "This is your home. Trips you create or join show up here." | — |
| 2 | New-trip modal (open it for the user) | `ai-trip-planner-input` | "Roammate's AI planner kicks off every trip — give it a city or vibe and it builds the bones." | — (static demo; we do not actually invoke the planner during tutorial) |
| 3 | Trip detail header | `trip-overview-header` | "This is your tutorial trip to New York. Members, dates, and a quick summary live here." | — |
| 4 | Timeline | `timeline-day-1` + `add-event-btn` | "Your day-by-day itinerary. Conflicts and travel times surface automatically." | "Tap an event to see details" |
| 5 | Brainstorm Chat | `brainstorm-chat-input` | "Brainstorm with AI to discover places to add. Each chat is private to you." | "Tap an existing suggestion to reply" → sends a preset user message, canned assistant reply |
| 6 | Brainstorm Bin | `brainstorm-bin-list` | "Ideas you extract from chat land here, just for you." | "Move one idea to the shared Idea Bin" → uses canned move endpoint |
| 7 | Idea Bin → Timeline → Map | `idea-bin-list`, `idea-move-to-timeline-btn`, `map-refresh-route-btn` | "The Idea Bin is shared with the group. Promote an idea, then refresh the route." | "Promote this idea, then refresh the route" → both succeed against canned fixtures |
| 8 | Concierge | `concierge-button` | "Concierge is your on-trip copilot — re-routes, recommendations, on-the-fly help. It's a Plus feature, but the tutorial gives you a free taste." | "Send a sample message" → canned reply |
| End | Dashboard | — | "You're all set. Want to keep the tutorial trip or remove it?" | "Delete tutorial trip" / "Keep for now" → calls `DELETE /api/tutorial/trip` or no-op |

Selectors live in `frontend/components/tutorial/steps.ts`; `data-tutorial` attributes are added inline at each call site (Dashboard, TripLanding, Timeline, BrainstormChat, IdeaBin, ConciergeActionBar, Map controls).

### 2.4 Gating persona & Plus modals
- `frontend/app/dashboard/page.tsx`: replace the existing `useEffect` that pops persona and Plus modals with a guard:
  ```
  if (tutorialStatus === 'not_started' || tutorialStatus === 'in_progress') return;
  // existing persona + Plus modal logic
  ```
- WelcomeModal opens automatically when `tutorialStatus === 'not_started'`.

### 2.5 Replay entry
- `frontend/app/profile/edit/page.tsx` (or a new "Help & Tour" subsection): add "Replay tutorial" row → calls `replay` mutation, navigates to Dashboard, opens WelcomeModal.

### 2.6 Read-only lock when `is_tutorial_completed`
- BrainstormChat input, Concierge input, Timeline edit affordances check `trip.is_tutorial_completed` → render a "Tutorial trip is read-only. Delete it or replay the tour." banner instead of inputs.

---

## 3. iOS Frontend Changes (SwiftUI)

Reference: `ios/Roammate/Theme/RoammateTheme.swift` (`roammateIndigo`, spring `0.35/0.85`, `RoammateRadius.card`).

### 3.1 Tutorial state
- New `ios/Roammate/Store/TutorialStore.swift` (`@MainActor ObservableObject`):
  - `@Published var status: TutorialStatus` (`.notStarted`, `.inProgress`, `.completed`, `.skipped`).
  - `@Published var currentStep: Int`.
  - `@Published var tutorialTripId: UUID?`.
  - Methods: `loadStatus()`, `start()`, `advance(to:)`, `skip()`, `complete()`, `replay()`, `deleteTutorialTrip()`.
- New `ios/Roammate/Network/TutorialService.swift` wrapping the new `/api/tutorial/*` endpoints. Sends `X-Client-Platform: ios` header.

### 3.2 Tutorial driver
- New `ios/Roammate/Views/Tutorial/TutorialCoordinator.swift`:
  - `EnvironmentObject` injected at `MainShell` level.
  - Owns the step script (mirrors web copy, adapted to iOS surfaces and navigation).
  - Drives tab switching and `NavigationStack` push as each step requires (e.g., push to `TripLandingView` for step 3).
- New `ios/Roammate/Views/Tutorial/SpotlightOverlay.swift`:
  - A `ZStack` overlay applied via `.overlay(alignment: .center)` at `ContentView`.
  - Uses `PreferenceKey` (`TutorialAnchorKey`) for target views to publish their `Anchor<CGRect>` to the overlay.
  - Cuts a rounded-rect hole in a semi-opaque scrim and renders a popover card (uses `RoammateTheme` tokens) anchored near the target.
  - Buttons: Prev, Next, Skip, optional "Try it".
- New `ios/Roammate/Views/Tutorial/WelcomeSheet.swift`: first-launch modal sheet with Start / Skip.

### 3.3 Step targets (iOS surfaces)
Mirrors the web script but maps to native screens:
- Dashboard → `DashboardView` trips section.
- Trip-creation AI chat → demo `TripCreationView`'s AI planner input (open via deep navigation, not actually executed).
- Trip overview → `TripLandingView` header.
- Timeline → `TimelineDrawerContent` first event.
- Brainstorm Chat → `BrainstormChatView` input bar.
- Brainstorm Bin → `BrainstormBinView` first item.
- Idea Bin + Move + Map → `IdeaBinView` → `PlanMapPage` route control.
- Concierge → `TripConciergeView` (this stub must be filled in enough to render a chat with canned messages — at minimum a list + input bar wired to backend; the stub's full implementation can be tracked as a separate task but this plan requires a viewable Concierge screen).

Each target view exposes its rect via:
```swift
.anchorPreference(key: TutorialAnchorKey.self, value: .bounds) { ["timeline-day-1": $0] }
```

### 3.4 Gating persona/paywall
- `ios/Roammate/Views/MainShell.swift` `evaluateOnboarding()`: prepend
  ```
  guard tutorialStore.status == .completed || tutorialStore.status == .skipped else { return }
  ```
  before the persona-sheet and Plus-sheet logic. Show `WelcomeSheet` instead when status is `.notStarted`.

### 3.5 Settings replay
- `ios/Roammate/Views/Profile/ProfileTabView.swift`: add a "Replay Tutorial" row in a new "Help" section that calls `tutorialStore.replay()` and routes to Dashboard.

### 3.6 Read-only lock when `is_tutorial_completed`
- `BrainstormChatView`, `TripConciergeView`, `TimelineDrawerContent`: when the trip's `isTutorialCompleted == true`, replace input bars with a "Tutorial trip — read only" footer and CTAs to delete or replay.

---

## 4. Design Notes (from /ui-ux-pro-max + /frontend-theme guidance)

- **Spotlight**: rounded-corner cutout, 8px padding around the target, scrim at `rgba(15,23,42,0.55)` (slate-900 / `roammateInk`).
- **Popover**: white surface, `RoammateRadius.card` / `rounded-2xl`, `RoammateShadow.card` / Tailwind `shadow-xl`, 320–360 px wide on web, full-width minus margins on iOS.
- **Typography**: title `text-base font-semibold` / `.headline.bold()`, body `text-sm text-slate-600` / `.subheadline` muted.
- **Buttons**: primary Next uses `bg-indigo-600` / `roammateIndigo`; Skip uses ghost / muted. "Try it" uses outlined indigo.
- **Motion**: enter/exit `transitionTimingFunction.expo` on web, `spring(0.35, 0.85)` on iOS.
- **Step indicator**: discrete dots row above the footer, indigo for active.
- **Accessibility**: focus trapped inside popover on web, `aria-modal="true"`, ESC = Skip, arrow keys = Prev/Next. iOS uses `accessibilityElement(children: .contain)` and VoiceOver announces step copy.

---

## 5. Verification

### Backend
- `pytest backend/tests/cross/test_tutorial_flow.py` end-to-end.
- Smoke-test in `backend/scripts/`: hit `/api/tutorial/start`, then `POST /api/{trip}/brainstorm/chat` with the mocked LLM client patched to raise — must not be called.
- Confirm `UsageCounter.brainstorm_messages` unchanged across the whole tutorial flow.
- Confirm DB integrity: replay then delete leaves no `Trip` with `is_tutorial=True` for that user.

### Web
- `pnpm dev` from `frontend/`. Register a fresh user, log in.
- Welcome modal appears; persona/Plus modals do not.
- Step through all 8 steps using Next and "Try it"; resume by reloading mid-step.
- Click Skip on step 4; reload — persona modal now appears, tutorial trip still present until deleted from Settings.
- Replay from `/profile/edit`; confirm a fresh tutorial trip appears.
- Delete from final-step modal; confirm trip disappears.
- Network tab: no calls to `/maps/*` enrichment endpoints or LLM endpoints originate from the tutorial trip.

### iOS
- Build & run on simulator. Fresh user.
- WelcomeSheet appears; persona/Plus sheets suppressed.
- Step through all 8 steps; close & reopen app mid-step → resumes.
- Replay from Profile → Help → Replay Tutorial.
- Confirm Concierge screen renders with canned messages and the input behaves; after completion, input is replaced by the read-only banner.
- Charles/Proxyman: no `places.googleapis.com` or LLM-host calls during tutorial.

---

## 6. Out of Scope (deliberately)

- Group / Notifications / Persona / Settings / People-page tour steps.
- iOS↔Web tutorial sync.
- Mid-trip Maps re-route with real polylines (we use seeded `DayRoute`).
- Analytics for funnel drop-off (can be added later via existing event pipeline).
- A11y for the iOS spotlight beyond VoiceOver basics (deep dive later if needed).

---

## 7. Critical Files

**Backend**
- `backend/app/models/all_models.py` (User + Trip columns)
- `backend/migrations/006_add_tutorial.sql` (new)
- `backend/app/services/entitlements.py` (bypass)
- `backend/app/services/tutorial_seed.py` + `tutorial_fixtures.py` (new)
- `backend/app/api/endpoints/tutorial.py` (new)
- `backend/app/api/endpoints/brainstorm.py`, `concierge.py`, `maps.py`, `idea_bin.py` (canned short-circuits)
- `backend/app/api/endpoints/trips.py` (expose `is_tutorial`, `is_tutorial_completed`)
- `backend/tests/cross/test_tutorial_flow.py` (new)

**Web**
- `frontend/hooks/useTutorial.ts` (new)
- `frontend/components/tutorial/{TutorialProvider,SpotlightOverlay,WelcomeModal,steps}.{tsx,ts}` (new)
- `frontend/app/layout.tsx` (wrap with provider)
- `frontend/app/dashboard/page.tsx` (gate persona/Plus, mount WelcomeModal)
- `frontend/app/trips/[id]/page.tsx`, `frontend/app/trips/page.tsx`, `frontend/components/trip/{Timeline,BrainstormChat,IdeaBin,ConciergeActionBar}.tsx`, `frontend/components/map/*` (add `data-tutorial` anchors + read-only states)
- `frontend/app/profile/edit/page.tsx` (Replay CTA)

**iOS**
- `ios/Roammate/Store/TutorialStore.swift` (new)
- `ios/Roammate/Network/TutorialService.swift` (new)
- `ios/Roammate/Views/Tutorial/{TutorialCoordinator,SpotlightOverlay,WelcomeSheet}.swift` (new)
- `ios/Roammate/Views/MainShell.swift` (gate persona/Plus, mount overlay)
- `ios/Roammate/Views/ContentView.swift` (inject env object)
- `ios/Roammate/Views/Dashboard/DashboardView.swift`, `Views/Trips/TripLandingView.swift`, `Views/Trips/Plan/{TimelineDrawerContent,IdeaBinView,PlanMapPage}.swift`, `Views/Trips/Brainstorm/{BrainstormChatView,BrainstormBinView}.swift`, `Views/Trips/SubPages/TripConciergeView.swift` (add `anchorPreference` + read-only states; flesh out Concierge stub minimally)
- `ios/Roammate/Views/Profile/ProfileTabView.swift` (Replay row)
