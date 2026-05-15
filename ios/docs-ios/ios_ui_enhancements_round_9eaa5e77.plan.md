---
name: iOS UI Enhancements Round
overview: "Five iOS UI fixes: widget label logic (Now/Up Next/Next), My Trips layout restructure, timeline dot colors, Idea Bin tap regression fix, and drag-to-reorder on Timeline with conflict resolution."
todos:
  - id: widget-labels
    content: "Fix widget label logic: Now / Up Next / Next with correct coloring"
    status: completed
  - id: trips-layout
    content: Move Add Trip FAB to toolbar inline with 3-dot menu; verify tab pill + list scroll behavior
    status: completed
  - id: dot-colors
    content: Change timeline hour dots from gray to lighter indigo shade
    status: completed
  - id: idea-tap-fix
    content: Fix Idea Bin card selection and expand tap regression
    status: completed
  - id: drag-reorder
    content: Implement drag-to-reorder on Timeline with conflict resolution and auto-reorder
    status: completed
isProject: false
---

# iOS UI Enhancements Round

## 1. Widget Label Logic (Now / Up Next / Next)

**File:** [ios/Roammate/Views/Dashboard/TodayWidgetCards.swift](ios/Roammate/Views/Dashboard/TodayWidgetCards.swift)

The `scheduledItems` computed property (line 167) currently labels all upcoming items as "Up next". Fix the labeling logic:

- If there is an **ongoing event**: label it "Now", the **first upcoming** event gets "Up Next", remaining (up to 1 more) get "Next".
- If there is **no ongoing event**: the **first upcoming** event gets "Up Next", remaining (up to 2 more) get "Next".
- Total items shown: at most 3.

Change the loop at lines 188-191 to track the index and apply the correct label. Also update the color mapping (line 226) to handle three labels: "Now" = `roammateAmber`, "Up Next" = `roammateIndigo`, "Next" = `roammateMuted`.

---

## 2. My Trips Page Layout Restructure

**File:** [ios/Roammate/Views/Trips/TripsTabView.swift](ios/Roammate/Views/Trips/TripsTabView.swift)

### 2a. Move Add Trip button to toolbar (inline with title)

- Remove `addTripFAB` (lines 248-270) and the conditional rendering at lines 47-49.
- Add a `+` button as a new `ToolbarItem(placement: .primaryAction)` next to the existing 3-dot menu. Both toolbar items should appear on the same row (use `ToolbarItemGroup(placement: .primaryAction)` to group them).

### 2b. Pin tab pill and make only list scrollable

Current layout is a `VStack { tabPill; tripsList }` where `tripsList` is a `ScrollView` containing the `LazyVStack`. The tab pill is already outside the `ScrollView`, so it should already be pinned. However, the `navigationTitle("My Trips")` with `.large` display mode causes the large title to scroll. Change to `.inline` title display mode **or** build a custom header that pins the title, the `+`/`...` buttons, and the tab pill above the scroll area. The simplest correct fix:

- Keep `.navigationBarTitleDisplayMode(.large)` for the native sticky behavior (large titles are sticky by default in `NavigationStack`). The tab pill is already outside the `ScrollView`, so it is already pinned.
- Verify the only issue is the FAB button placement. If the title/pill are already static, just moving the FAB to toolbar solves it.

---

## 3. Timeline Hour Dots Color

**File:** [ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift)

Line 175: Change `Color.roammateBorder` to `Color.roammateIndigoTint` (the lighter shade of indigo already defined in [RoammateTheme.swift](ios/Roammate/Theme/RoammateTheme.swift) at line 11, `#EDE9FE`).

If `roammateIndigoTint` is too light/invisible, use `Color.roammateIndigo.opacity(0.25)` instead for a visible but subtle indigo.

---

## 4. Idea Bin Tap Regression Fix

**File:** [ios/Roammate/Views/Trips/Plan/IdeaRow.swift](ios/Roammate/Views/Trips/Plan/IdeaRow.swift)

**Root cause:** The previous fix (from the `day_date` migration session) replaced the parent `onTapGesture` with a `Button` in `.background { }`. The `.background` button uses `Color.clear` as its label, which has zero hit area in SwiftUI -- `Color.clear` does not register taps. This means neither card selection nor expand-on-tap works.

**Fix:** Replace the `.background { Button { ... } label: { Color.clear } }` pattern with a proper `contentShape(Rectangle())` + `onTapGesture` approach, but use `.simultaneousGesture` or restructure the view to not interfere with child `Button` elements. The correct approach:

- Remove the `.background { Button ... }` block (lines 134-147).
- Add `.contentShape(Rectangle())` to the outer VStack.
- Add `.onTapGesture { ... }` **after** the `.overlay` modifier, calling the appropriate handler (toggle or tap).
- The child `Button` elements (delete, time edit, vote) already use `.buttonStyle(.plain)` which should receive priority in SwiftUI hit-testing over `onTapGesture`. If not, wrap the entire card in a `Button` and move the child buttons to use `highPriorityGesture`.

The key insight: SwiftUI `Button` has higher hit-testing priority than `onTapGesture`, so `onTapGesture` on the parent should not block child `Button` taps. The previous bug was that `onTapGesture` was consuming all taps -- this was likely because it was placed before child buttons in the view hierarchy. Placing it after `.overlay` (at the end of the modifier chain) ensures correct behavior.

---

## 5. Drag-to-Reorder on Timeline with Conflict Resolution

**File:** [ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift](ios/Roammate/Views/Trips/Plan/TimelineDrawerContent.swift)

The `handleReorder` function already exists (line 192) but is disconnected since `List` was replaced with `LazyVStack`.

### Approach: Use SwiftUI drag-and-drop with `draggable`/`dropDestination` or `onDrag`/`onDrop`

Since `LazyVStack` does not support `onMove`, implement manual drag-to-reorder:

1. **Add `@State private var draggingEventId: Int?`** to track the dragged item.
2. **On each `TimelineRow`**, add `.onDrag { ... }` to provide the event ID as `NSItemProvider`.
3. **On each row's container**, add `.onDrop(of:delegate:)` with a custom `DropDelegate` that:
   - On `dropEntered`: reorder `currentEvents` in the local state (move the dragged item to the hovered position).
   - On `performDrop`: persist the new order by calling `handleReorder` (which already calls `store.reorderEvent` for each event).
4. **After drop (in `handleReorder`)**: The existing `conflictIds` computed property will automatically recalculate based on the new sort order, and `TimelineRow` will re-render with updated `isConflict` flags -- red borders will appear/disappear as needed.

### Auto-reorder after drop

After the drag completes, if there are conflicts, optionally auto-resolve by sorting events by `startTime`. However, per the user's request ("full conflict resolution after the drop and auto-reorder"), implement:

- After `handleReorder` persists the new sort orders, recalculate conflicts.
- If any conflicts exist, auto-sort events by `startTime` ascending, then persist the new sort orders again.
- Show a brief haptic feedback when conflicts are resolved.

### Store changes

**File:** [ios/Roammate/Store/TripDetailStore.swift](ios/Roammate/Store/TripDetailStore.swift)

Add a `batchReorderEvents(dayDate:events:)` method that takes the full reordered list and sends all sort-order updates in one pass (to avoid N sequential network calls). The existing `reorderEvent` can be called in a loop as a fallback.
