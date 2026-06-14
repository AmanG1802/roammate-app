# [43] Timeline Drawer — Native Sheet + UIKit Bridge

## Context

The timeline drawer on the Plan sub-page (PlanMapPage) is implemented as a custom SwiftUI
`BottomDrawer` component — a `VStack` inside a `ZStack` that simulates a sheet by animating
its `.frame(height:)`. During a drag gesture, this triggers a full SwiftUI layout pass on every
finger-movement event (~60–120/sec), causing visible jitter and dropped frames, especially
when the map is simultaneously rendering polylines or loading tiles.

The fix is to replace `BottomDrawer` with iOS's native `UISheetPresentationController`
(via SwiftUI's `.sheet` + `presentationDetents`), augmented with a UIKit bridge to allow
scrolling content at any detent. This matches the pattern already used in `AIChatDrawer`
and `PlanTripDrawer` elsewhere in the app.

---

## Root Causes of Jitter (All Four)

### 1. `.frame(height:)` mutation on every gesture tick — primary culprit
`BottomDrawer.swift:59`
```swift
.frame(height: max(0, targetH - dragOffset))
```
Every `DragGesture.onChanged` mutates `@State var dragOffset`, triggering a full SwiftUI
layout recalculation through `GeometryReader → VStack → ScrollView → TimelineDrawerContent`.
Layout is expensive; doing it 120×/sec during a drag causes jitter.

### 2. Implicit animation conflict during live tracking
`BottomDrawer.swift:71`
```swift
.animation(.spring(response: 0.35, dampingFraction: 0.85), value: current)
```
This animation is on the same container whose height changes during drag. SwiftUI
sometimes applies the spring curve to the raw tracking movement — fighting the finger.

### 3. `@State` for dragOffset goes through full SwiftUI diffing
`@GestureState` is purpose-built for gesture tracking and bypasses part of the diffing
pipeline. Plain `@State` adds the full ObservableObject/view-diff overhead every frame.

### 4. `ScrollView` + `DragGesture` gesture recognizer competition
Even though the drag is on the handle only, `ScrollView` participates in the same gesture
recognizer tree. iOS runs hit-testing and gesture arbitration on every touch event, adding
latency. The scroll is only disabled in the minimised detent, not during active drags,
so recognizers compete mid-drag.

---

## How UX Changes — Interaction by Interaction

### Dragging the drawer up/down
**Before:** `dragOffset` state → SwiftUI layout on main thread → full ZStack re-render.
Jitter visible whenever the map is busy (polylines, tile loading).

**After:** UIKit gesture recognizer on a dedicated thread path, running at the compositor
level. Tracks at full ProMotion (120 fps on Pro devices) regardless of main thread load.
Indistinguishable from Apple Maps.

### Snapping to detents
**Before:** `withAnimation(.spring(...))` on `.frame(height:)` — spring interpolates layout
sizes on every animation tick on the main thread.

**After:** `UISpringTimingParameters` on the render server (off main thread). Physically
accurate bounce + settle. Using `predictedEndTranslation` (velocity-aware), fast flicks
snap to the correct detent even without full travel distance.

### Scrolling the timeline at mid detent
**Before:** 100ms+ gesture arbitration delay before iOS decides: "scroll list or drag
drawer?" Results in list sticking before scroll starts, or drawer sticking before it moves.

**After (default native):** Upward scroll at mid detent expands to full detent first,
then scrolling begins — the same UX as Apple Maps.

**After (with UIKit bridge):** `prefersScrollingExpandsWhenScrolledToEdge = false` —
scrolling works immediately at any detent. Appropriate for the timeline because users
need to scan 5–6 events without committing to full-screen mode.

### Scroll-to-dismiss handoff
**After:** At full detent, scroll to top of list → drag down → sheet collapses to mid
detent. One continuous gesture through two systems. Cannot be replicated in custom
SwiftUI without a `UIViewRepresentable` wrapper around `UIScrollView`.

### Map interactivity behind the drawer
**Before:** `Map` and `BottomDrawer` are siblings in a `ZStack`. Gesture recognizers
cover full screen; touches near drawer edge can accidentally fire map interactions.

**After:** `presentationBackgroundInteraction(.enabled)` — map remains fully interactive
through the sheet. Touch routing is precise: sheet touches go to sheet, map touches
(through the area above the sheet) go to the map.

### Rubber-band over-scroll
**After:** Drag past top/bottom detent → sheet rubber-bands and springs back.
Makes the boundary feel physical rather than hard-stopped.

### Drag indicator (handle)
**Before:** Custom `Capsule` shape; must aim precisely at the small handle.

**After:** `.presentationDragIndicator(.visible)` — system handle; entire top area of
sheet (including `DayTabsBar`) is a drag target. Matches iOS muscle memory.

### Keyboard avoidance
**After:** Sheet automatically adjusts detent when a keyboard appears (e.g., if inline
time-editing ever adds a text field). System coordinates keyboard + sheet animation
as a single transition.

### What stays the same
- `TimelineDrawerContent` — list, day tabs, timeline rows, drag-to-reorder: untouched
- Map overlay controls: day badge, refresh route, map style — still on map layer
- Event selection callouts — unchanged
- All state: `selectedDayIndex`, `drawerDetent` equivalents passed as bindings

---

## Realistic Options

| Approach | Scroll at mid-detent | Smoothness | Effort |
|---|---|---|---|
| Custom BottomDrawer fixes (offset + GestureState + disable anim) | Yes | Good | Low |
| Native sheet, default | No (expands to large first) | Best | Low |
| **Native sheet + UIKit bridge** | **Yes** | **Best** | **Medium** |
| Custom UIViewRepresentable sheet from scratch | Yes | Best | Very High |

---

## Recommendation / Decision Freeze

**Selected approach: Native sheet + UIKit bridge**

Rationale:
- The timeline is the primary interaction surface on the Plan page — unlike Apple Maps
  search results, users need to browse 5–6 events at mid-detent without expanding to full
- `prefersScrollingExpandsWhenScrolledToEdge = false` is a 15-line UIKit shim, not a
  major engineering investment
- `AIChatDrawer` and `PlanTripDrawer` already use native `.sheet()` — this aligns the
  codebase and removes the only custom drawer component
- `BottomDrawer.swift` can be deleted entirely (used in exactly one place)
- No UX regression: the map stays interactive, all three detents are preserved, the
  tutorial anchor is relocated to the sheet content

---

## Implementation Plan

### Step 1 — Add UIKit scroll bridge (`ScrollableAtAnyDetent.swift`)
Create a new file in `Theme/`:

```swift
// Theme/ScrollableAtAnyDetent.swift
import SwiftUI

/// Introspects the enclosing UISheetPresentationController and disables
/// the default "scroll to expand" behaviour so list content scrolls freely
/// at any detent.
struct ScrollableAtAnyDetent: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        UIViewController()
    }
    func updateUIViewController(_ vc: UIViewController, context: Context) {
        DispatchQueue.main.async {
            vc.sheetPresentationController?
                .prefersScrollingExpandsWhenScrolledToEdge = false
        }
    }
}
```

### Step 2 — Rewrite `PlanMapPage.swift`

Replace the `BottomDrawer(...)` block (lines 226–233) with a `.sheet` modifier on the
outer `ZStack`. Key API surface:

```swift
// State
@State private var drawerDetent: PresentationDetent = .fraction(0.6)

// On the ZStack:
.sheet(isPresented: .constant(true)) {
    TimelineDrawerContent(selectedDayIndex: $selectedDayIndex)
        .environmentObject(store)
        .presentationDetents(
            [.height(140), .fraction(0.6), .large],
            selection: $drawerDetent
        )
        .presentationDragIndicator(.visible)
        .presentationBackgroundInteraction(.enabled(upThrough: .fraction(0.6)))
        .presentationCornerRadius(28)
        .interactiveDismissDisabled()
        .background { ScrollableAtAnyDetent() }
}
```

Notes:
- `.constant(true)` — sheet is always present, never dismissed
- `.interactiveDismissDisabled()` — prevents accidental full dismiss
- `.presentationBackgroundInteraction(.enabled(upThrough: .fraction(0.6)))` — map is
  interactive when sheet is at mid or minimised; blocked at full (intentional: at full
  detent the user is focused on the timeline)
- `drawerDetent` type changes from `DrawerDetent` enum to `PresentationDetent`

### Step 3 — Relocate tutorial anchor

`BottomDrawer` previously accepted `panelAnchorID: "timeline-day-1"` and applied
`.tutorialAnchorIf(panelAnchorID)` to the visible panel. In the native sheet, apply the
tutorial anchor directly inside `TimelineDrawerContent`:

In `TimelineDrawerContent.swift`, add `.tutorialAnchor("timeline-day-1")` to the
outermost `VStack` in `body`.

Verify in `TutorialCoordinator.swift` / `TutorialSteps.swift` that the spotlight
highlight still resolves correctly against the new anchor location.

### Step 4 — Delete `BottomDrawer.swift`

The file is used in exactly one place (`PlanMapPage.swift`) which is being replaced.
Delete `Theme/BottomDrawer.swift` and the `DrawerDetent` enum (no other usages confirmed).

### Step 5 — Update `drawerDetent` type references in `PlanMapPage`

`PlanMapPage` declared `@State private var drawerDetent: DrawerDetent`. Replace with
`@State private var drawerDetent: PresentationDetent = .fraction(0.6)`.
The old `scrollDisabled` logic in `BottomDrawer` (disabled at minimised) is no longer
needed — the native sheet handles scroll/expand coordination.

---

## Files Modified

| File | Change |
|---|---|
| `Theme/BottomDrawer.swift` | **Delete** |
| `Theme/ScrollableAtAnyDetent.swift` | **Create** — UIKit bridge (~15 lines) |
| `Views/Trips/Plan/PlanMapPage.swift` | Replace `BottomDrawer` with `.sheet` modifier; update `drawerDetent` state type |
| `Views/Trips/Plan/TimelineDrawerContent.swift` | Add `.tutorialAnchor("timeline-day-1")` to outermost `VStack` |

No changes to: `TimelineRow`, `DayTabsBar`, `TripSubPagesHost`, `PlanPaneView`, any
stores, or any backend / web code.

---

## Verification

1. **Run on device** (not simulator — ProMotion differences are device-only): open a trip → Plan tab
2. **Drag handle** up and down: confirm zero jitter, finger-perfect tracking
3. **Fast flick** upward from minimised: should snap to mid or large based on velocity
4. **Scroll timeline at mid detent**: list should scroll immediately without expanding first
5. **Scroll to top at large detent → drag down**: sheet should collapse to mid
6. **Tap map pins while sheet is at mid detent**: map interaction should work through sheet
7. **Tap map pins while sheet is at large detent**: sheet blocks map (intentional)
8. **Tutorial spotlight**: verify "timeline-day-1" anchor highlights the drawer panel correctly
9. **Add/delete events, switch days**: confirm all timeline interactions work normally
10. **Drag-to-reorder events**: confirm `onDrag`/`onDrop` delegates still fire correctly
    inside the native sheet scroll view
