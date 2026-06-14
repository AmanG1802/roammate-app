# [51] Timeline Native Sheet — Option A Implementation

## Context

Decision made in [50]. We are implementing:

1. **Option A** — Replace `BottomDrawer` with a native `UISheetPresentationController`. The Idea Bin is accessed via a two-tab strip at the top of the drawer (`Timeline | Idea Bin`), not a swipe gesture. `PaneSlider` is removed.

2. **Floating Refresh Route button** — The button moves from the fixed map overlay to a position that floats right above the sheet's top edge at all times. It tracks the sheet pixel-perfect during a drag gesture (live 60–120fps via `CADisplayLink`), and fades out when the sheet reaches full detent.

---

## Architecture After This Change

```
TripSubPagesHost
  └─ PlanPaneView  (no more PaneSlider / TabView swipe)
       └─ PlanMapPage
            ├─ Map
            ├─ Map overlay (day badge, map style, fit-all)
            ├─ Floating Refresh Route button  ← NEW: position driven by sheetTopY
            └─ .sheet(isPresented: .constant(true))
                 ├─ SheetPositionTracker  ← NEW: CADisplayLink feeds sheetTopY back
                 ├─ DrawerTabStrip (Timeline | Idea Bin)  ← NEW
                 └─ (if drawerTab == .timeline)  TimelineDrawerContent
                    (if drawerTab == .ideaBin)   IdeaBinView
```

The outer `PaneSlider` and `IdeaBinView` as a peer page are removed entirely. Idea Bin lives inside the sheet. No more gesture conflict with any TabView.

---

## New Files

### `Theme/SheetPositionTracker.swift`

A `UIViewRepresentable` that embeds a zero-height UIView inside the sheet and starts a `CADisplayLink` to read that view's Y position in window coordinates every frame. Publishes the sheet's live top-edge Y position back to SwiftUI via `@Binding<CGFloat>`.

```swift
// Theme/SheetPositionTracker.swift
import SwiftUI

struct SheetPositionTracker: UIViewRepresentable {
    @Binding var sheetTopY: CGFloat

    func makeUIView(context: Context) -> TrackerView {
        TrackerView(sheetTopY: $sheetTopY)
    }

    func updateUIView(_ uiView: TrackerView, context: Context) {}

    static func dismantleUIView(_ uiView: TrackerView, coordinator: ()) {
        uiView.stop()
    }
}

final class TrackerView: UIView {
    private var sheetTopY: Binding<CGFloat>
    private var displayLink: CADisplayLink?

    init(sheetTopY: Binding<CGFloat>) {
        self.sheetTopY = sheetTopY
        super.init(frame: .zero)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        let link = CADisplayLink(target: self, selector: #selector(tick))
        link.add(to: .main, forMode: .common)
        displayLink = link
    }

    required init?(coder: NSCoder) { fatalError() }

    func stop() {
        displayLink?.invalidate()
        displayLink = nil
    }

    @objc private func tick() {
        guard let window else { return }
        let topY = convert(.zero, to: window).y
        // Only push update when the value meaningfully changes (avoids
        // thrashing SwiftUI when the sheet is stationary).
        if abs(topY - sheetTopY.wrappedValue) > 0.5 {
            sheetTopY.wrappedValue = topY
        }
    }
}
```

**Note:** The 0.5pt threshold on the tick suppresses SwiftUI re-renders when the sheet is stationary (at a snapped detent), eliminating unnecessary CPU work at rest. During a drag this fires at full display refresh rate.

---

### `Theme/ScrollableAtAnyDetent.swift`

Already in the existing plan [43]. Unchanged here — ~15 lines, sets `prefersScrollingExpandsWhenScrolledToEdge = false`.

---

## Modified Files

### `Views/Trips/Plan/PlanPaneView.swift`

Remove the `PaneSlider` wrapper. `IdeaBinView` is no longer a peer page — it lives inside `PlanMapPage`'s sheet.

```swift
struct PlanPaneView: View {
    // ... environment objects unchanged

    var body: some View {
        PlanMapPage()
    }
    // applyTutorialPane() becomes unnecessary — tutorial navigation
    // to Idea Bin is now handled by drawerTab state inside PlanMapPage
}
```

---

### `Views/Trips/Plan/PlanMapPage.swift`

**State changes:**
```swift
// Remove:
@State private var drawerDetent: DrawerDetent = .fraction(0.6)

// Add:
@State private var drawerDetent: PresentationDetent = .fraction(0.6)
@State private var drawerTab: DrawerTab = .timeline
@State private var sheetTopY: CGFloat = UIScreen.main.bounds.height

enum DrawerTab { case timeline, ideaBin }
```

**Replace the `BottomDrawer` block (lines 227–234) with:**
```swift
.sheet(isPresented: .constant(true)) {
    VStack(spacing: 0) {
        SheetPositionTracker(sheetTopY: $sheetTopY)
            .frame(height: 0)

        DrawerTabStrip(selection: $drawerTab)

        Group {
            if drawerTab == .timeline {
                TimelineDrawerContent(selectedDayIndex: $selectedDayIndex)
            } else {
                IdeaBinView()
            }
        }
        .environmentObject(store)
    }
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

**Floating Refresh Route button** — replace the current inline `refreshRouteButton` in the map overlay `VStack` with a positioned overlay anchored to `sheetTopY`:

Remove `refreshRouteButton` from the `HStack` in the top map controls. Add it as a separate overlay on the `ZStack`:

```swift
// On the outer ZStack, after the map overlay VStack:
.overlay(alignment: .bottom) {
    GeometryReader { geo in
        let buttonBottom = geo.size.height - sheetTopY + geo.safeAreaInsets.top
        // sheetTopY is in window coords; convert to local ZStack coords
        refreshRouteButton
            .padding(.bottom, 12)
            .position(
                x: geo.size.width / 2,
                y: sheetTopY - geo.frame(in: .global).minY - 28  // 28 = half button height + gap
            )
            .opacity(drawerDetent == .large ? 0 : 1)
            .animation(.easeInOut(duration: 0.2), value: drawerDetent == .large)
    }
}
```

> Implementation note: exact coordinate math depends on whether `sheetTopY` is in window space vs the ZStack's local space. Use `GeometryReader` with `.global` coordinate space to offset correctly. The `SheetPositionTracker` view is embedded at the very top of the sheet content so its window Y = the sheet's top edge Y.

**Remove** the `BottomDrawer` import / `DrawerDetent` type references throughout.

---

### `Views/Trips/Plan/TimelineDrawerContent.swift`

No structural changes — the `VStack` body stays identical. The tutorial anchor `"timeline-day-1"` at `Color.clear.frame(height: 1)` (line 94) stays in place.

---

### New component: `DrawerTabStrip`

A small two-tab pill added to `TimelineDrawerContent.swift` or as its own file in `Views/Trips/Plan/`. Lives at the very top of the sheet content, above `DayTabsBar`.

```swift
struct DrawerTabStrip: View {
    @Binding var selection: PlanMapPage.DrawerTab

    var body: some View {
        HStack(spacing: 0) {
            tab(label: "Timeline", icon: "calendar", tab: .timeline)
            tab(label: "Idea Bin", icon: "lightbulb", tab: .ideaBin)
        }
        .padding(4)
        .background(Capsule().fill(Color.roammateBackground))
        .padding(.horizontal, RoammateSpacing.md)
        .padding(.vertical, 8)
    }

    private func tab(label: String, icon: String, tab: PlanMapPage.DrawerTab) -> some View {
        Button {
            HapticManager.selection()
            withAnimation(.spring(response: 0.3, dampingFraction: 0.85)) {
                selection = tab
            }
        } label: {
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .bold))
                Text(label)
                    .font(.system(size: 12, weight: .bold))
            }
            .foregroundStyle(selection == tab ? Color.roammateEmerald : Color.roammateMuted)
            .padding(.horizontal, 14)
            .padding(.vertical, 7)
            .background(
                Capsule().fill(selection == tab ? Color.roammateEmeraldTint : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .frame(maxWidth: .infinity)
    }
}
```

Tab colors: **Timeline** uses `roammateEmerald` (matches Plan sub-page accent). **Idea Bin** uses `roammateAmber` (matches Brainstorm accent — ideas/lightbulb). The pill background matches `roammateBackground`.

---

### `Theme/BottomDrawer.swift`

**Delete.** Used only in `PlanMapPage`, which is being replaced.

---

## Refresh Route Button — Behaviour Summary

| Sheet state | Button behaviour |
|---|---|
| Minimised (140pt) | Visible, floating 12pt above the sheet's top drag indicator |
| Mid detent (60%) | Visible, floating 12pt above sheet top — moves pixel-perfect as user drags |
| Dragging between detents | Tracks finger position at 60–120fps via `CADisplayLink` |
| Full detent (large) | Fades out with `.easeInOut(0.2)` animation |
| Mid → Full snap | Fades out as sheet springs to large |
| Full → Mid snap | Fades in as sheet springs back down |

The day badge and map controls (fit-all, map style) remain in the top-left/right of the map overlay — their position is not affected by the sheet.

---

## Drag-to-Reorder Safeguard

As discussed in [50]: if real-device testing shows the sheet starts collapsing during a downward reorder drag, add this to `TimelineDrawerContent`:

```swift
// In the .onDrag modifier:
.onDrag {
    draggingEventId = event.id
    drawerDetent = .large  // lock sheet open during drag
    return NSItemProvider(object: String(event.id) as NSString)
}
// In performDrop inside TimelineDropDelegate — reset after drop completes
```

This requires passing `$drawerDetent` into `TimelineDrawerContent` as a binding, which is a small additional parameter.

---

## Tutorial Anchor Migration

`BottomDrawer` previously accepted `panelAnchorID: "timeline-day-1"` and applied `.tutorialAnchorIf()` to the entire panel. This is already handled: `TimelineDrawerContent` has `.tutorialAnchor("timeline-day-1")` on the `Color.clear.frame(height: 1)` at line 94. No change needed.

Verify `TutorialScript` / `TutorialCoordinator` still resolves this anchor in its new sheet context.

---

## Files Changed Summary

| File | Change |
|---|---|
| `Theme/SheetPositionTracker.swift` | **Create** — CADisplayLink UIKit bridge (~50 lines) |
| `Theme/ScrollableAtAnyDetent.swift` | **Create** — scroll bridge (~15 lines) |
| `Theme/BottomDrawer.swift` | **Delete** |
| `Views/Trips/Plan/PlanPaneView.swift` | Remove `PaneSlider`; render `PlanMapPage` directly |
| `Views/Trips/Plan/PlanMapPage.swift` | Replace `BottomDrawer` with `.sheet`; add `drawerTab`/`sheetTopY` state; floating Refresh Route button |
| `Views/Trips/Plan/DrawerTabStrip.swift` | **Create** — two-tab Timeline / Idea Bin switcher |
| `Views/Trips/Plan/TimelineDrawerContent.swift` | No structural change; verify tutorial anchor |

No backend, web, or other iOS changes.

---

## Verification Checklist

Run all tests on a **physical device** (not simulator).

1. Open a trip → Plan tab: native sheet appears at mid detent, `Timeline` tab is active
2. Drag handle up to large detent: Refresh Route button fades out smoothly
3. Drag handle back down: button fades back in, tracks the sheet perfectly during drag
4. Fast flick up/down: button springs with the sheet to the snapped position
5. Tap **Idea Bin** tab: sheet content swaps to IdeaBinView, tab indicator switches to amber
6. Tap **Timeline** tab: switches back, selected day index preserved
7. Select ideas in Idea Bin → "Add to Timeline": `AddToTimelineSheet` opens at mid; expand sheet to large if it feels cramped
8. Tap event row to expand inline; tap again to collapse
9. Tap "Edit Time": time picker sheet opens above the timeline sheet
10. Vote, move to bin, restore skipped item: all work
11. Drag-to-reorder two events including a downward drag: sheet does not collapse
12. Tap map pin at mid detent: callout appears; at large detent it's blocked (intentional)
13. Map pinch/zoom/pan at mid detent: works through sheet
14. Refresh Route button taps correctly at minimised and mid detent
15. Tutorial: `timeline-day-1` spotlight highlights the timeline panel correctly
16. Tutorial pane switching: verify `applyTutorialPane()` in `PlanPaneView` (or its replacement) still navigates to Idea Bin tab when tutorial step requires it
