# iOS Plan Map — Drawer-aware popup, recenter & route clearing

## Context

On the iOS trip Plan map (`PlanMapPage.swift`), two interactions break once the
Timeline drawer is raised above its lowest detent:

1. **Place popup is hidden behind the drawer.** Tapping a timeline marker shows a
   `MapCalloutSheet` with the place's details. That callout is rendered *inside*
   the map ZStack, bottom-anchored with a `Spacer()` (PlanMapPage.swift:170–195).
   The native drawer sheet draws on top of the whole map, so at `.fraction(0.6)`
   (half) or `.large` (full) it physically covers the bottom strip where the
   callout sits. The popup is only visible at `.height(140)` (low). Users browsing
   at half detent tap a marker and see nothing.

2. **Recenter ignores the drawer.** The recenter button calls `fitCamera()`
   (PlanMapPage.swift:465–482), which fits all markers to a region centered on the
   **full** screen. At half detent the drawer covers the bottom ~60%, so markers
   land behind it. Recenter should fit markers into only the *visible* map area
   above the drawer — full preview at low detent, the upper slice at half detent.

3. **Stale route polylines linger after the timeline changes.** When the timeline
   signature changes (event added/removed/retimed/relocated, or all events sent
   back to the idea bin), both platforms only *mark* the route stale — the existing
   polyline stays drawn on the map. iOS `checkRouteStaleness` (TripDetailStore.swift
   :332-338) just sets `isRouteStale = true` and leaves `routeOverlays` on the map;
   web `clearRouteVisuals()` (GoogleMap.tsx:313-322) is only fired on *day change*,
   not on a same-day signature change. Result: a now-wrong route line lingers, and
   in the "all items back to bin" case a random leftover polyline remains. The
   polylines should be **removed** the moment the signature diverges, leaving the
   stale/refresh affordance to invite a recompute.

The app already solves the "float above the live drawer edge" problem for the
Refresh Route button via `floatingRouteCluster` + `SheetPositionTracker`/`sheetTopY`
(PlanMapPage.swift:202–312). We reuse that exact mechanism for both fixes.

**Decisions (confirmed with user):**
- Popup floats just above the live drawer edge at any detent (reuse `sheetTopY`).
- While a popup is shown, the Refresh Route cluster is hidden; it restores on dismiss.
- Recenter fits markers to the visible map area, and **also auto-refits when the
  drawer settles at a new detent**.
- When the timeline signature changes, the drawn polylines are removed immediately
  (not just marked stale) on **both** iOS and web; the stale/refresh affordance
  stays so the user can recompute.

> Concerns 1–2 (popup, recenter) are iOS-only. Concern 3 (route clearing) touches
> both `ios/` and `frontend/`.

## Part A — iOS map UX (concerns 1–2): `ios/Roammate/Views/Trips/Plan/PlanMapPage.swift`

### 1. Float the place / leg callouts above the drawer edge

Move the two callout views (`MapCalloutSheet` and `RouteLegCallout`) out of the
bottom-anchored `VStack` inside the map ZStack (lines 170–195) and into a new
`floatingCalloutCluster` overlay built on the **same** `GeometryReader` +
`sheetTopY` math as `floatingRouteCluster` (lines 269–312).

- Add a `@ViewBuilder var floatingCalloutCluster` that:
  - Computes `localSheetTop = sheetTopY - geo.frame(in: .global).minY` and a
    `buttonCenterY`-style anchor, then positions the callout with its **bottom
    edge** ~12pt above the drawer edge (use `.position` and `.fixedSize`, mirroring
    the route cluster; anchor by bottom so taller callouts grow upward).
  - Renders `MapCalloutSheet` when `selectedEventId` resolves to an event, and
    `RouteLegCallout` when `selectedLegIndex` is set (same resolution logic that
    currently lives at lines 171–195).
  - Constrains width (e.g. horizontal padding 16 / `frame(maxWidth:)`) so it
    matches today's inset look.
  - Hides itself at `.large` detent (map not meaningfully visible there) and when
    `!visible`, mirroring the route cluster's opacity guard.
- Attach it as a second `.overlay { floatingCalloutCluster }` next to the existing
  `.overlay { floatingRouteCluster }` at line 203. Keep the existing
  `.animation(...)` transitions on selection.
- Remove the callout block from the in-ZStack `VStack` (lines 170–195); that VStack
  keeps only the top day-badge/controls row + `Spacer()`.

### 2. Hide the Refresh Route cluster while a callout is shown

In `floatingRouteCluster`'s opacity guard (line 308), add a condition so the
cluster fades out when a callout is active:

```swift
let calloutActive = selectedEventId != nil || selectedLegIndex != nil
.opacity((drawerDetent == .large || !visible || drawerTab == .ideaBin || calloutActive) ? 0 : 1)
```

Add `.animation(.easeInOut(duration: 0.18), value: calloutActive)` so the swap is
smooth. (Tapping empty map already clears both selections at lines 145–149, which
restores the Refresh button.)

### 3. Make `fitCamera()` drawer-aware

Rework `fitCamera()` (lines 465–482) so the markers fit the **visible** map slice
above the drawer rather than the full screen. Use the already-tracked `sheetTopY`
and screen height:

- `let screenH = UIScreen.main.bounds.height`
- `let visibleFraction = max(min(sheetTopY / screenH, 1), 0.2)` — guards the initial
  `sheetTopY == screenH` case (≈1.0 → full screen) and clamps a sane floor.
- Keep the existing bounding-box center (`markerCenterLat/Lng`) and base padded
  span. Then **only on latitude** (drawer covers the bottom, full width):
  - Inflate so the markers occupy the visible fraction:
    `latitudeDelta = paddedLatSpan / visibleFraction`.
  - Shift the region center south so markers sit in the visible top slice. With
    north = up, screen-fraction `p` maps to `lat = center + (0.5 - p) * latDelta`;
    the visible center is at `p = (sheetTopY/2)/screenH`, so
    `center.latitude = markerCenterLat - (0.5 - p) * latitudeDelta`.
- Longitude span/center keep the current 1.4×-padded bounding-box logic unchanged.

This naturally yields: low detent (`sheetTopY` high → fraction ≈0.85) ≈ full-preview
fit; half detent (fraction ≈0.4) fits markers into the upper visible slice.

### 4. Auto-refit on detent change

Add to the existing modifier chain (near lines 233–248):

```swift
.onChange(of: drawerDetent) { _, _ in fitCamera() }
```

`sheetTopY` is live-updated by `SheetPositionTracker`; `drawerDetent` settles on the
final detent, so `fitCamera()` reads the resolved `sheetTopY`. Skip the refit at
`.large` (map hidden) with an early `guard drawerDetent != .large` inside the
handler or `fitCamera()`.

## Part B — Clear route polylines on timeline-signature change (concern 3)

Both platforms already have the fingerprint comparison and the polyline-clearing
primitive; they just don't fire the clear on a *same-day* signature change. Wire
that up on each side.

### iOS — `ios/Roammate/Store/TripDetailStore.swift`

In `checkRouteStaleness(dayDate:)` (lines 332-338), when the fingerprint diverges,
also drop the drawn overlays — keep `isRouteStale = true` and the stored
`routeFingerprint`/`routeResponse` so the amber "Refresh Route" affordance and
staleness comparison keep working:

```swift
func checkRouteStaleness(dayDate: String) {
    let events = eventsByDay[dayDate] ?? []
    let currentFp = RouteService.computeFingerprint(events: events)
    if let stored = routeFingerprint, stored != currentFp {
        isRouteStale = true
        routeOverlays = []          // remove the now-wrong polylines from the map
    }
}
```

- This is already called from `PlanMapPage.onChange(of: store.eventsByDay)`
  (PlanMapPage.swift:244-248), so add/move events, retime, relocate, or skip →
  fingerprint changes → overlays cleared.
- "All items back to bin": every event becomes skipped / leaves the day, so
  `computeFingerprint` (RouteService.swift:400-428, which filters out skipped /
  unlocated events) yields a different hash → overlays cleared. No leftover line.
- The floating Refresh cluster (Part A / existing `floatingRouteCluster`) still
  shows the stale state via `isRouteStale`; when fewer than 2 routable events
  remain it is naturally disabled (`refreshDisabled`, PlanMapPage.swift:91-93).

### Web — `frontend/components/map/GoogleMap.tsx`

Extend the existing day-change clear effect (lines ~240-250) so it also clears when
the local event fingerprint diverges within the same day, mirroring the day-change
branch:

```ts
useEffect(() => {
  if (
    routeSnapshot &&
    (routeSnapshot.filterDay !== currentDayKey ||
     routeSnapshot.fingerprint !== currentFingerprint)
  ) {
    clearRouteVisuals();   // setMap(null) on all polylines + leg labels
    setMockRoute(null);
    setLastRouteData(null);
  }
}, [currentDayKey, currentFingerprint, routeSnapshot]);
```

- `currentFingerprint` comes from `evFingerprint(events)` (lines 133-140), which
  includes `events.length` and each event's `id:start:end`. Moving every event to
  the bin shrinks `events`, changing the fingerprint → visuals cleared.
- `clearRouteVisuals()` already removes all Google `Polyline` objects and leg labels
  via `setMap(null)` (lines 313-322); calling it again is idempotent, and the
  `setMockRoute(null)`/`setLastRouteData(null)` are no-ops once already null, so no
  render loop.
- We intentionally do **not** clear on `backendStale` alone — a freshly fetched
  stored-but-stale route should still render (drawn with its stale styling) on load;
  only an in-session signature change wipes the line. `routeSnapshot` is left intact
  so the `stale` memo (lines 215-250) keeps the Refresh affordance lit.
- The auto-fetch effect is keyed on `[tripId, currentDayKey]`, so this does **not**
  trigger a refetch — it only clears. The user's Refresh action redraws and resets
  `routeSnapshot` as today.

## Notes / edge cases
- Parts A is iOS-only; Part B touches both iOS and web. No backend changes — the
  backend already recomputes `is_stale` per GET (maps.py:316-361).
- Web's `evFingerprint` format differs from the backend/iOS SHA-256 fingerprint;
  that mismatch is pre-existing and out of scope here — we only rely on the web
  fingerprint changing when the local timeline changes, which it does.
- `MapCalloutSheet.swift` and `RouteLegCallout` need no internal changes; only their
  placement/host moves.
- Reuse existing helpers — `sheetTopY`, `SheetPositionTracker`, `allMarkers`,
  `dayEvents`, `store.routeOverlays`. No new models or services.
- Keep the empty-state overlay and top controls untouched.

## Verification
- Build the iOS app (Xcode / `xcodebuild` for the Roammate scheme) and run on a
  simulator with a trip that has ≥2 located timeline events plus a refreshed route.
- Popup: at **half** detent, tap a marker → callout appears just above the drawer
  edge and the Refresh Route button hides; tap empty map → callout dismisses and
  Refresh restores. Repeat at **low** detent (callout still floats correctly) and
  confirm it hides at **full** detent. Tap a route leg → leg callout floats the same.
- Drag the drawer up/down with a callout open → it tracks the live drawer edge
  (same smoothness as the Refresh button today).
- Recenter: at **low** detent, tap recenter → all markers fit the near-full preview.
  At **half** detent, tap recenter → all markers sit in the upper visible slice, none
  hidden behind the drawer. Drag between low ↔ half → camera auto-refits each time.
- Regression: single-marker day still respects the `0.02` min-span floor and stays
  centered in the visible area.
- Route clearing (iOS): with a drawn route, edit the timeline (add/move/retime an
  event) → the polyline disappears immediately and the Refresh button shows the
  amber "Timeline changed" state. Send all events back to the bin → no leftover
  polyline remains. Tap Refresh → route recomputes and redraws.
- Route clearing (web): repeat the same edits in the browser → drawn polyline +
  leg labels clear on the signature change; binning all events leaves no leftover
  line; Refresh redraws. Confirm a freshly loaded stored-but-stale route still
  renders on initial page load (not wiped) and that switching days still clears.
