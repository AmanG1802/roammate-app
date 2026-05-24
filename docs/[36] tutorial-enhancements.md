# [36] Tutorial Enhancements — Web & iOS Parity

## Context

The onboarding tour (shipped in [33]) needs polish on **both** platforms. On Web:
step ordering is non-monotonic, popups appear before their page/section is
loaded (the floating Step 9 popover in the screenshot), the Concierge step never
switches modes without a hard reload, replay-from-settings skips the Welcome
banner, and the tutorial trip appears not to delete. On **iOS** the tour is
fundamentally incomplete: the `TutorialCoordinator` only draws the spotlight over
whatever screen is currently visible — it **never navigates** the app to the
relevant tab / sub-page / pane. So a step's anchor only resolves if the user
manually got there; otherwise the popover floats centred. iOS also needs the same
step order as Web.

Goal: on both platforms the tour **always loads the relevant page/section first,
then presents the popup** on the correct element, with smooth transitions and no
floating/misplaced popovers.

## Investigation findings

- **Deletion is NOT a backend bug.** Reproduced `delete_tutorial_trip` and the
  full `DELETE /trips/{id}` endpoint logic (incl. `notification_service`) against a
  freshly seeded tutorial trip in the running container — both succeed. The user's
  symptom is a **client-side stale/cached trip list** on the dashboard.
- **Web Concierge stays on Plan page**: `frontend/app/trips/page.tsx` sets `mode`
  via `useState(initialMode)` and never re-syncs when `searchParams` change
  (`page.tsx:50–58`). `router.push(?mode=concierge)` updates the URL, not state.
- **Web overlay shows before navigation completes** — `TutorialProvider` renders
  `SpotlightOverlay` in parallel with `router.push`; missing target → centred popover.
- **iOS navigation model** (each level owns private `@State`):
  1. Tab — `MainShell.selection: AppTab`
  2. Dashboard's own `NavigationStack` `path` opens a trip via `path.append(trip)`
     → `navigationDestination(for: Trip.self)` → `TripLandingView` (`DashboardView.swift:24,46,77`)
  3. `TripLandingView.subPageDestination: SubPage?` → pushes `TripSubPagesHost`
  4. `TripSubPagesHost.currentPage: SubPage` (plan/brainstorm/concierge/people)
  5. Pane sub-tab — `PlanPaneView.page` (0=map/timeline,1=ideas) and
     `BrainstormPaneView.page` (0=chat,1=bin)
- iOS anchors present: `dashboard-trips`, `trip-overview-header`,
  `timeline-day-1`, `brainstorm-chat-input`, `brainstorm-bin-list`, `idea-bin-list`,
  and `concierge-button` (currently on **PlanMapPage's refresh button** — wrong).
  **Missing**: `new-trip-btn` (Step 2). The dashboard's plan entry is the `ChatFAB`
  (`DashboardView.swift:64`).

---

## A. Backend — `backend/app/api/endpoints/tutorial.py` + `tutorial_seed.py`

1. Add `POST /api/tutorial/reset`: delete the tutorial trip and set
   `status=not_started, step=0` for the platform. (Web replay-from-settings calls
   this so the Welcome banner shows again.) Leave `/replay` for iOS.
2. Harden `delete_tutorial_trip`: NULL `notification.trip_id` for the trip before
   deletion (mirror the manual endpoint) so it always deletes cleanly.

## B. Web

- **Step reorder** (`frontend/components/tutorial/steps.ts`) → monotonic flow
  (landing → brainstorm → plan → concierge). Renumber `step` fields:
  5 brainstorm-chat, 6 brainstorm-bin, 7 timeline, 8 idea-bin (unchanged), 9 concierge.
  Point Step 9 `target` at the **Concierge chat panel** (per user choice), not the
  bottom action bar.
- **Load page first, then popup** (`TutorialProvider.tsx` + `SpotlightOverlay.tsx`):
  compute `routeReady = urlMatches(expandRoute(step.route, trip_id), pathname, search)`;
  only `open` the overlay when `routeReady`. In `SpotlightOverlay`, hold the
  popover/ring hidden until the target rect is measured (poll a few frames; ~500ms
  fallback to centre for routeless/targetless steps); `scrollIntoView` then measure
  after settle; tighten the cutout spring so Steps 1–2 land cleanly.
- **`/trips` mode sync** (`frontend/app/trips/page.tsx`): add `useEffect` setting
  `mode` from `rawMode` whenever the search param changes (fixes Concierge step).
- **Sample message** (`TutorialProvider` + Concierge/Brainstorm panels): after the
  `POST`, dispatch `tutorial:tryit`; the panels listen and reload messages to animate
  the sent message + reply.
- **Replay from settings** (`frontend/app/profile/edit/page.tsx` + `useTutorial.tsx`):
  add `reset()`; replace `replay()` call with `reset()` then `router.push('/dashboard')`
  → `WelcomeModal` ("Welcome to Roammate") shows → **Start** seeds + Step 1.
- **Deletion** (`frontend/app/dashboard/page.tsx`): refetch the trip list with
  `cache: 'no-store'` after delete; ensure `onTripUpdate()` re-runs the list query.
  Verify both finish-prompt and manual card delete in-browser.

## C. iOS — bring tour to parity (the main new work)

**C1. Step reorder + anchors** (`Views/Tutorial/TutorialSteps.swift`)
- New order: 1 dashboard, 2 planTrip, 3 tripOverview, **4 brainstormChat,
  5 brainstormBin, 6 timeline, 7 ideaBin**, 8 concierge, 9 wrapUp.
- Add `.tutorialAnchor("new-trip-btn")` to the dashboard `ChatFAB`
  (`DashboardView.swift:64`).
- Move the `concierge-button` anchor off `PlanMapPage`'s refresh button; add a
  `concierge-input` anchor on the Concierge composer in
  `Views/Trips/SubPages/TripConciergeView.swift` (the "Ask Concierge…" TextField,
  line 57). Update Step 8's `anchorID` accordingly.

**C2. Navigation driver — new `TutorialNavigator`** (drives the nested state)
- Add a computed `desiredLocation(for step:)` (on `TutorialStore` or a small helper):
  ```swift
  struct TutorialLocation: Equatable {
      var openTrip: Bool      // push tutorial trip onto Dashboard path
      var subPage: SubPage?   // nil = stay on TripLanding
      var paneIndex: Int?     // 0/1 within plan or brainstorm pane
  }
  ```
  Map: steps 1–2 → `{openTrip:false}`; step 3 → `{openTrip:true}`;
  4 → `{openTrip, .brainstorm, 0}`; 5 → `{.brainstorm,1}`; 6 → `{.plan,0}`;
  7 → `{.plan,1}`; 8 → `{.concierge}`; 9 → landing/concierge.
- The tour stays on the **Dashboard tab** (Steps 1–2 live there; avoids a tab
  switch). `start()`/`replay()` reload `tripStore` so the tutorial `Trip` exists to push.
- Each navigation-owning view observes `tutorial.currentStep` (only when
  `tutorial.isActive`) and applies its slice via `.onChange`:
  - `DashboardView` — append the tutorial `Trip` to `path` when `openTrip` and not
    already pushed; pop to root when `openTrip` is false.
  - `TripLandingView` — set `subPageDestination = location.subPage` (push host) / nil.
  - `TripSubPagesHost` — set `currentPage = location.subPage`.
  - `PlanPaneView` / `BrainstormPaneView` — set `page = location.paneIndex` (init from
    it on appear, and react to step changes while their subPage is current).

**C3. Gate the popup until the screen is ready** (`Views/Tutorial/TutorialCoordinator.swift`
+ `SpotlightOverlay.swift`)
- In `overlayBody`, render the dim scrim immediately but only show the **popover +
  ring** once the step's `anchorID` is present in `anchors` (i.e. the target screen
  mounted and published its rect). For `anchorID == nil` (wrapUp) show centred after a
  short delay. Add a ~1.5s fallback so a never-resolving anchor still shows centred.
- This makes every popup wait for navigation + mount, then land on the element —
  matching Web's "load page first" behaviour. Keep the existing spring on `rect`;
  because the popover only appears after the anchor resolves, it animates in place
  rather than flying across the screen.

**C4. Sample-message animation** (`TutorialCoordinator.runTryIt` + stores)
- Route the sample send through the relevant store (`BrainstormStore` / Concierge
  view's send path) instead of calling the service directly, so the message + reply
  appear with the existing chat animation. The build fix
  (`BrainstormService.sendMessage` → `.chat`) is already applied.

---

## Verification

- **Backend**: `cd backend && pytest tests/cross/test_tutorial_flow.py`; manually
  hit `/api/tutorial/reset`.
- **Web**: run the tour end-to-end — each popup appears only after its page/section
  loads; Steps 1–2 land on the grid then New-trip button; Concierge step switches to
  the Concierge panel with a clean layout; sample messages send + animate;
  replay-from-settings shows the Welcome banner; finishing or manually deleting the
  tutorial trip removes the card.
- **iOS**: build succeeds; replay the tour from Profile — the app auto-navigates
  Dashboard → tutorial trip → Brainstorm (chat→bin) → Plan (timeline→ideas) →
  Concierge, each popup appearing only after its screen is on-screen and landing on
  the correct element; Back steps reverse the navigation; sample messages animate;
  finishing offers to delete the trip.
</content>

---

## Iteration 2 — iOS popup placement & anchor fixes

Reported after the first pass: misplaced/empty spotlight rings and popovers
overlapping content on several iOS steps. Root causes + fixes:

- **Empty/misplaced rings (Steps 1, 5, 6, 7).** The anchors were attached to
  `Color.clear.frame(height: 1)` spacer strips, so the ring landed on a 1px line.
  Re-anchored to real elements:
  - Step 1 `dashboard-trips` → the "My Trips" `SectionHeader` (`DashboardView.swift`).
  - Step 5 `brainstorm-bin-list` → the bin `header` row (`BrainstormBinView.swift`).
  - Step 7 `idea-bin-list` → the idea-bin `header` row (`IdeaBinView.swift`).
  - Step 6 `timeline-day-1` → the `DayTabsBar` (`TimelineDrawerContent.swift`).
- **Popover placement (`TutorialStep.placement`, new `PopoverPlacement`).** Each
  step now declares where its card sits so it never covers the thing it explains:
  - `.top` for chat steps (4 Brainstorm, 8 Concierge) and Step 2 (bottom FAB) —
    keeps the input bar + the just-sent message visible.
  - `.bottom` for the list/region steps (1, 3, 5, 6, 7); flips to top if the anchor
    is itself in the lower half.
  - `.center` for the anchorless wrap-up.
  `SpotlightOverlay` now measures the card height (`CardHeightKey`) and pins it
  flush to the chosen edge, centred horizontally, animating between positions.
- **Step 3 reliably opens the Trip Landing page.** `applyTutorialNav` no longer
  trusts the `tutorialTripPushed` flag alone — it re-pushes whenever `path` is
  empty, observes `tutorial.tutorialTripId`, and resets the flag if the stack is
  cleared. The else-branch is guarded so a non-tutorial user is never yanked back.

iOS build: `** BUILD SUCCEEDED **`.

---

## Iteration 3 — coordinate-space fix, region spotlights, plan-trip demo parity

### Critical: cutout vs ring misalignment (Steps 1, 2, 4, general)
The bright cutout sat exactly one status-bar-inset *above* the indigo ring. Cause:
`SpotlightOverlay`'s scrim `Canvas` uses `.ignoresSafeArea()` (origin at the
screen's top-left) while the ring is positioned in the GeometryReader's space
(origin below the status bar). Fix: offset the Canvas hole by
`geometry.safeAreaInsets` so cutout and ring line up exactly.

### Region spotlights (Steps 5, 6, 7 in the new numbering: bins + drawer)
- Added `TutorialStep.spotlightHeight` — grows the spotlight downward from the
  anchor's top edge. Set to 330 on the Brainstorm Bin and Idea Bin steps so the
  highlight wraps the header **plus the first ~2 cards**.
- Timeline step now anchors the **whole drawer**: `BottomDrawer` gained an
  optional `panelAnchorID` (applied to the visible panel, not the full-screen
  container); `PlanMapPage` passes `"timeline-day-1"`. Placement set to `.top`
  so the popover sits over the map and the entire drawer stays highlighted.

### Plan-trip demo parity (new Steps 2–3)
iOS now matches the web's `plan-trip-demo` + `plan-preview`:
- Step count is now **10** (added `planPreview`). Step 2 gets a **"Try Now"**
  action (`.planTripDemo`).
- `PlanTripStore.runTutorialDemo()` typewriters a canned NYC prompt, sits in the
  planning state, then shows `tutorialPreview` (canned, no LLM) — mirroring
  `runTutorialPlanDemo` on web.
- "Try Now" posts `.tutorialStartPlanDemo`; `DashboardView` opens `PlanTripDrawer`
  in `demoMode`. Because the system sheet covers the spotlight overlay, the
  preview-step guidance is rendered **inline** in the drawer (`tutorialPreviewHint`).
- The drawer's button reads **"Create Trip and Take Me There"** in demo mode and
  calls `onDemoCreate` → skips the real POST, closes the sheet, and advances to
  the trip-overview step (the seeded tutorial trip is then pushed by
  `applyTutorialNav`). `TutorialScript.number(of:)` resolves step numbers by id.

iOS build: `** BUILD SUCCEEDED **`.

## Iteration 4 — Back-navigation polish + Step 2 "Try Now" as primary

### Back button no longer flashes the spotlight over the outgoing page
`SpotlightOverlay` now gates the spotlight (cutout hole + ring + popover) behind
a `revealed` flag. On every step change the `.task(id: step.number)` sets
`revealed = false` (scrim drops to a flat dim with no hole), waits ~340ms for the
page/navigation transition to settle, then sets `revealed = true`. Combined with
the existing requirement that the target rect be published (`padded != nil`), the
spotlight only appears on the *destination* page — so pressing Back renders the
previous page first, then reveals its popup. Reveal is animated
(`.easeInOut(0.28)` on `revealed`, opacity transition on the ring), giving a
clean dim → navigate → reveal feel in both directions.

### Step 2: "Next" replaced by "Try Now"
- `TutorialStep` gained `advanceViaTryIt` (set on Step 2). When true, the popover
  hides the "Next" button and renders **Try Now** as the filled primary CTA in
  the bottom row (the separate outlined try-it chip is suppressed). Completing the
  plan demo advances the tour, so a separate Next is redundant.

### Why "Try Now" sometimes did nothing — fixed
`TutorialCoordinator.runTryIt` had a single early `guard tutorial.tutorialTripId
!= nil` covering all try-it actions. The plan demo is fully canned and creates
nothing, but the guard bailed silently whenever the seeded trip id hadn't loaded
yet — so the tap appeared to do nothing. Fix: the `.planTripDemo` case posts its
notification unconditionally; the `tutorialTripId` guard now only wraps the
sample-message sends (which act on the live trip).

iOS build: `** BUILD SUCCEEDED **`.

### Step 3 → 4: Trip Landing sometimes didn't load (popup floated over dashboard)
`TutorialStore.advance` updates `currentStep` only after a network round-trip.
The old `onDemoCreate` set `showPlanTrip = false` and kicked off `advance` at the
same time, so when the response arrived the `path.append(trip)` in
`applyTutorialNav` raced the sheet's dismiss animation — SwiftUI intermittently
dropped the push, leaving the Trip Landing page unloaded and Step 4's popover
falling back to centred over the dashboard. Fix: `onDemoCreate` now only sets a
`advanceAfterDemoDismiss` flag and closes the sheet; the `advance` (and thus the
trip push) runs in the sheet's `onDismiss`, once the stack is settled. A plain
swipe-to-dismiss leaves the flag unset, so it just closes the planner.

iOS build: `** BUILD SUCCEEDED **`.

### Back (Step 5 → 4): sub-page host failed to pop, popup floated over Brainstorm
Going Back from a sub-page step to the trip-overview step left the Brainstorm page
on screen with Step 4's popover over it. Two compounding causes:
- `TutorialStore.advance` updated `currentStep` only after a network round-trip,
  so the step change and the navigation weren't synchronous. Fix: `advance` now
  sets `currentStep` optimistically (when active and changed) before the call, so
  every `.onChange(of: currentStep)` fires immediately in one transaction.
- `TripLandingView.applyTutorialSubPage` mutated the `navigationDestination`
  binding (`subPageDestination = nil`) synchronously from inside that
  currentStep-driven update — SwiftUI intermittently coalesces/drops a nav-binding
  mutation made mid-transaction, so the host didn't pop. Fix: defer the
  `subPageDestination` push/pop to the next runloop tick (`DispatchQueue.main.async`)
  so SwiftUI processes it in a clean transaction. (`@State` has a `nonmutating
  set`, so setting it from the escaping closure is valid.)

iOS build: `** BUILD SUCCEEDED **`.
