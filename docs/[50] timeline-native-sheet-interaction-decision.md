# [50] Timeline Drawer — Native Sheet Interaction Decision

## Context

The Plan page (`PlanMapPage`) uses a custom `BottomDrawer` — a SwiftUI component that simulates a sheet by animating its position. In RM-049 we replaced it with iOS's native `UISheetPresentationController`. In RM-051 we reverted because the native sheet broke the swipe-right gesture that takes users from the Plan/Map view to the Idea Bin. The jitter fix was salvaged and applied to `BottomDrawer` (using GPU-only `.offset` instead of layout-pass `.frame`), and the native sheet was dropped.

This document maps every interaction on the Plan page against both approaches so we can make a confident product decision before implementing anything.

---

## Architecture Context (Why the Conflict Exists)

```
TripSubPagesHost
  └─ PlanPaneView
       └─ PaneSlider (TabView with .page swipe style)
            ├─ Page 0: PlanMapPage
            │   ├─ Map
            │   ├─ Map overlay controls (day badge, refresh route, map style)
            │   └─ BottomDrawer  ← ZStack sibling, same UIView layer
            │       └─ TimelineDrawerContent
            └─ Page 1: IdeaBinView
```

The swipe-right-to-Idea-Bin gesture works because `PaneSlider`'s `TabView` can capture horizontal swipes from anywhere on screen. When we replace `BottomDrawer` with a native `.sheet()`, iOS puts the sheet in a **separate modal UIViewController** above the TabView. Any touch inside that modal — including a horizontal swipe — is consumed by the sheet before the TabView ever sees it. The TabView's swipe gesture stops working.

---

## Full Interaction Table

| Interaction | How it works today (BottomDrawer) | With Native Sheet | Why |
|---|---|---|---|
| **Swipe right → Idea Bin** | Swipe anywhere on screen; TabView captures it | ❌ Broken | Sheet is a modal layer above the TabView; horizontal swipes on the sheet never reach the TabView's gesture recognizer |
| **Swipe left → back to Plan** | Same TabView swipe | ❌ Unreachable (reaching Idea Bin is already broken) | Same root cause |
| **Drag drawer handle up/down** | Custom handle with `DragGesture`; GPU offset, no jitter after RM-051 fix | ✅ Better — native ProMotion tracking, finger-perfect at 120fps | UIKit runs the gesture off the main thread at compositor level |
| **Fast-flick to snap detent** | `predictedEndTranslation` in `onEnded` | ✅ Better — velocity-aware physics spring | `UISpringTimingParameters` runs on the render server, not the main thread |
| **Scroll timeline at mid detent** | Works; scroll is disabled at minimised detent to avoid gesture conflict | ✅ Better — scrolls immediately at any detent, no expand-first | `prefersScrollingExpandsWhenScrolledToEdge = false` via UIKit bridge |
| **Scroll to top then drag down to collapse** | Not possible — scroll and drawer are separate gesture recognizers | ✅ Bonus interaction | Native sheet handles this as one continuous gesture |
| **Tap event row to expand inline** | Works — row grows in place with spring animation | ✅ Works unchanged | `.onTapGesture` on the row fires normally inside a native sheet |
| **Tap "Edit Time" button → time picker sheet** | Opens a `.sheet` at `.medium` detent | ✅ Works — sheets can stack on iOS 16+ | iOS supports presenting a sheet from inside another sheet; the picker appears above the timeline sheet |
| **Thumbs up / Thumbs down vote** | Tap buttons inside expanded row | ✅ Works unchanged | Simple tap gestures |
| **"Move to Bin" button (tray icon)** | Tap button in top-right of each row | ✅ Works unchanged | Simple tap |
| **"Restore" button (skipped items)** | Tap button on skipped row | ✅ Works unchanged | Simple tap |
| **Drag-to-reorder events** | Long-press + drag on row; works reliably today | ⚠️ Works but needs device testing (see detail below) | UIKit DnD runs at high privilege but edge-case conflict with sheet pan gesture is possible |
| **Tap day tab to switch days** | Tap `DayTabsBar` inside drawer | ✅ Works unchanged | Tap gesture |
| **Add day / delete day** | Buttons inside `TimelineDrawerContent` | ✅ Works unchanged | Tap gesture; confirmation dialog works inside a sheet |
| **Tap map pin at mid/min detent** | Map layer is a ZStack sibling; always hittable | ✅ Works | `.presentationBackgroundInteraction(.enabled(upThrough: .fraction(0.6)))` passes touches through |
| **Tap map to deselect** | Map `.onTapGesture` | ✅ Works at mid/min detent | Same background interaction passthrough |
| **Map pinch/zoom/pan** | Always works | ✅ Works at mid/min; ❌ blocked at large detent (intentional) | Background interaction is disabled at large detent by design — user is focused on the timeline |
| **Tap route polyline** | Map layer | ✅ Works at mid/min detent | Same passthrough |
| **Refresh Route button** | Map overlay — ZStack layer above everything | ✅ Works — it lives on the map layer, not inside the sheet | Not affected by the sheet at all |
| **Map style / fit-all buttons** | Map overlay | ✅ Works unchanged | Same as above |
| **Rubber-band bounce at detent boundaries** | Hard stop (no physical feel) | ✅ Bonus — sheet bounces then springs back | Native UIKit behavior, cannot replicate in custom SwiftUI |
| **Keyboard avoidance (text field in sheet)** | Manual handling required | ✅ Bonus — automatic | Sheet + keyboard animate together as a system transition |

---

## Drag-to-Reorder: Detailed Analysis

**How it works today:** Each event row has `.onDrag` and `.onDrop(delegate:)`. The user long-presses a row (~0.5s hold), which activates UIKit's DnD system, then drags up/down to reorder. The 0.5s hold means the gesture is clearly distinct from a scroll and the system doesn't confuse the two. Works reliably today.

**Inside a native sheet:**
The risk is a specific edge case. When a user drags a row *downward* near the bottom of the sheet, the sheet's own pan-to-collapse gesture could activate and start collapsing the sheet, treating the downward drag as "try to dismiss."

However, three things work in our favour:
1. The 0.5s long-press hold before a drag session starts means the sheet has already observed the initial touch as stationary and did not begin a pan-to-dismiss.
2. `interactiveDismissDisabled()` prevents the sheet from dismissing entirely even if a pan gesture fires.
3. UIKit's DnD system, once a drag session is active, runs at a higher priority than gesture recognizers and typically holds the sheet stable for the duration.

**The one scenario to test on a real device:** Dragging a row from near the top of the list *downward* past the currently visible area. If the sheet starts collapsing mid-drag, the mitigation is to lock the sheet detent to `.large` when a drag begins and restore it when the drop completes — a 2-line change using `drawerDetent` state.

---

## The Three Options

### Option A — Keep Native Sheet, Replace Swipe-Right with a Button

**What changes for the user:**
Swiping right to reach the Idea Bin is gone. Instead there is a clearly visible button or tab that takes the user to the Idea Bin. The map + timeline experience is fully native — smooth, physics-correct, zero jitter. Everything else about the Plan page is identical.

The Idea Bin is essential to planning — users constantly move ideas from the Bin to the timeline — so whichever button we add must be prominent and feel like a natural part of the workflow, not an afterthought.

**Possible button placements (best to least preferred):**

1. **Tab strip at the top of the drawer** — Add a two-tab pill (`Timeline | Idea Bin`) at the very top of `TimelineDrawerContent`, above `DayTabsBar`. Tapping "Idea Bin" swaps the drawer content to show `IdeaBinView` inline; tapping "Timeline" switches back. Both surfaces live inside the same native sheet. This is the most ergonomic placement: the drawer already has the user's attention, the tab is right there without any extra gesture. The `PaneSlider` in `PlanPaneView` is removed (Plan is just `PlanMapPage`; Idea Bin is accessed through the in-drawer tab). This also **eliminates the outer TabView entirely**, removing the root cause of the gesture conflict permanently. Even if we ever add native sheet back in the future, the conflict will not return.

2. **Pill inside the day section header** — A small "Bin (12 ideas) →" tappable link next to the event count. Contextually useful — "this day has 3 stops and there are 12 ideas you could add." Low visual weight; feels like a shortcut rather than a navigation element. Good complement to option 1 but not a replacement.

3. **Floating "Bin" button on the map overlay** — Sits alongside the existing map controls (fit-all, map style) in the top-right corner, or as a pill button on the top-left. Always visible regardless of drawer detent. Tapping pushes `IdeaBinView` as a full-screen overlay or NavigationStack push. Less contextually connected to the drawer content, but always reachable even when the drawer is minimised.

4. **Inside the `TripSubPagesHost` top bar** — Add an "Ideas" icon to the top nav bar that sets `currentPage` to a new `.ideas` SubPage. This makes the Idea Bin a top-level sub-page alongside Brainstorm and People, decoupling it from the Plan surface. Changes the information architecture — Idea Bin is no longer "part of Plan" — which may or may not fit product intent, but does make it discoverable from any sub-page.

5. **Bottom of the drawer event list** — A "View Idea Bin →" text link at the very end of the timeline. Appears after all events. Low friction once found, but requires scrolling to discover; not appropriate as the primary entry point.

**UX summary:** Option A gives the best possible drawer feel. Placement 1 (tab strip) is the right call: it matches the iOS pattern used by apps like Notes (accounts vs. folders), makes the Idea Bin equally visible as the Timeline at a glance, and the drawer is already the space users focus on when planning. Users who previously swiped will adapt quickly — tapping a labeled tab is arguably more discoverable than an invisible swipe gesture for new users.

---

### Option B — Keep Native Sheet, Move Idea Bin Inside the Sheet

**What changes for the user:**
The Idea Bin moves inside the sheet as a second panel. The user swipes horizontally *within the sheet* to switch between Timeline and Idea Bin. This gesture starts inside the sheet's own content, so there is no conflict with any outer TabView (which is removed). The map always stays visible and interactive above the sheet.

**How the swipe works at mid-detent:**
At mid-detent the sheet occupies roughly 60% of screen height (~500px on iPhone 15). The sheet content is a `TabView` with `.page` style containing two panels: Timeline (left) and Idea Bin (right). Pager dots at the top of the sheet indicate which panel is active — the same visual language as the current `PaneSlider` pager dots. The user swipes right-to-left on the sheet content to slide to the Idea Bin panel. The map stays visible above the sheet throughout. The swipe is horizontal within the sheet, so the sheet's own pan-to-collapse gesture (which is vertical) does not interfere.

**At minimised detent (~140px):**
Only the tab indicator strip and the handle are visible. A swipe in this state would be ambiguous (is it a panel switch or a detent change?). The natural behaviour is: at minimised, a swipe expands the sheet to mid-detent first; panel switching happens once the sheet is at mid or large detent. This is acceptable since at 140px neither panel's content is meaningfully usable anyway.

**What gets more complex:**
- `IdeaBinView` has a `selectionToolbar` that slides up from the bottom when the user selects items to promote to the timeline. Inside a sheet at mid-detent, this toolbar eats into the ~500px of space, leaving less room for the idea list. At large detent this is perfectly comfortable; at mid-detent it is slightly cramped.
- `IdeaBinView` presents `AddToTimelineSheet` (a `.sheet` at `.medium` detent) when promoting ideas. This creates a sheet-within-a-sheet. On iOS 16+ this works, but at mid-detent the outer sheet and the inner sheet can visually overlap in a way that looks cramped. The natural solve is to expand the outer sheet to large detent before opening the promotion flow — which could be done automatically on "Select" tap.
- The outer `PlanPaneView` / `PaneSlider` is removed entirely. `TripSubPagesHost` stays unchanged.

**UX summary:** Option B preserves the horizontal swipe as muscle memory but relocates it from "anywhere on screen" to "inside the sheet." For users who use the Plan page heavily — switching back and forth between Timeline and Bin constantly while dragging ideas to days — this feels very natural. The map always stays visible, which is a material improvement over today where the Idea Bin pushes the map completely off screen. The main friction point is the nested-sheet sizing at mid-detent during the "Add to Timeline" flow; this is solvable but requires attention.

---

### Option C — Keep BottomDrawer (Current State)

**What stays the same:**
Everything. All interactions work exactly as today. The RM-051 jitter fix is already in place.

**What you live with:**
- Drawer tracking runs on the main thread. If the map is loading tiles or rendering polylines simultaneously, there is a small residual jitter risk (much less than before RM-051, but not structurally zero).
- Snapping physics uses SwiftUI's `interactiveSpring` rather than UIKit's render-server spring — visually close but not identical to Apple Maps.
- No rubber-band bounce at detent boundaries.
- The scroll-to-collapse handoff gesture is not available.
- Custom handle (small tap target) instead of the full-width system drag indicator.

**UX summary:** Lowest-risk path. Interactions are solid and all tested. If the Plan page becomes heavier (animated markers, more polylines, denser events), main-thread jitter under load may resurface more noticeably.

---

## Recommendation Summary

| | Idea Bin access | Drawer smoothness | Interaction completeness | Implementation scope |
|---|---|---|---|---|
| **Option A (tab in drawer)** | Tap a labeled tab — slightly different but more discoverable | Best (native UIKit) | All interactions retained | Medium — restructure `PlanPaneView`, add tab UI to `TimelineDrawerContent` |
| **Option B (Bin inside sheet)** | Swipe inside the sheet — preserves gesture as muscle memory | Best (native UIKit) | All interactions retained; nested sheet sizing needs care | Medium-high — restructure `PlanPaneView`, `TabView` inside sheet, handle mid-detent nested sheet |
| **Option C (BottomDrawer)** | Swipe — unchanged | Good (residual jitter risk under map load) | Everything works | Zero — already done |

**For heavy Plan-page users** who switch between Timeline and Bin constantly: **Option B** preserves the swipe and gives native smoothness — the best of both worlds at the cost of structural rework.

**For simplicity and long-term stability**: **Option A** with a tab strip in the drawer is clean, kills the gesture conflict permanently, and is arguably more discoverable for new users.

**For zero risk right now**: **Option C** is done.

---

## Files That Would Change

**Option A:**
| File | Change |
|---|---|
| `Views/Trips/Plan/PlanPaneView.swift` | Remove `PaneSlider`; render `PlanMapPage` directly |
| `Views/Trips/Plan/PlanMapPage.swift` | Replace `BottomDrawer` with `.sheet`; add `drawerPage` state (`timeline` vs `ideaBin`) |
| `Views/Trips/Plan/TimelineDrawerContent.swift` | Add tab strip at top switching between Timeline and Idea Bin views |
| `Theme/ScrollableAtAnyDetent.swift` | Create — UIKit bridge (~15 lines) |
| `Theme/BottomDrawer.swift` | Delete |

**Option B:**
| File | Change |
|---|---|
| `Views/Trips/Plan/PlanPaneView.swift` | Remove `PaneSlider`; render `PlanMapPage` directly |
| `Views/Trips/Plan/PlanMapPage.swift` | Replace `BottomDrawer` with `.sheet`; sheet content is a `TabView(.page)` containing Timeline and Idea Bin panels |
| `Theme/ScrollableAtAnyDetent.swift` | Create |
| `Theme/BottomDrawer.swift` | Delete |

No backend or web changes for any option.

---

## Verification Checklist (When Implemented)

1. Run on a **physical device** — ProMotion jitter differences are device-only
2. Drag handle: finger-perfect tracking, zero jitter even while map loads polylines
3. Fast flick up from minimised: snaps to mid or large based on velocity
4. Scroll timeline at mid detent: list scrolls immediately, no expand-first
5. **Reach Idea Bin** via the new mechanism (tap tab / swipe inside sheet) and return to Timeline
6. **Promote an idea** from Bin to timeline: `AddToTimelineSheet` opens correctly; verify sizing at mid-detent
7. Tap a timeline event row: expands inline with spring animation
8. Tap "Edit Time": time picker sheet opens above timeline sheet, saves correctly
9. Vote thumbs up / thumbs down: works, persists
10. Move event to Bin button: event disappears from timeline, appears in Bin
11. Restore a skipped event: RESTORE button works, event re-activates
12. **Drag-to-reorder** two events including a downward drag: sheet does not collapse mid-drag
13. Tap a map pin while sheet is at mid detent: map callout appears
14. Tap map pin while sheet is at large detent: sheet blocks it (intentional)
15. Tutorial spotlight on `timeline-day-1` anchor highlights correctly
