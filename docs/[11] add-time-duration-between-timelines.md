# Timeline Bin: Inline Travel Time Between Items

## Issue

The Timeline Bin shows itinerary cards in time order with the new gap-dot indicator showing idle hours, but it gives the user **no signal of how long it actually takes to travel from one place to the next**. A user planning back-to-back stops can't tell if "30 minutes between items" is plenty of buffer or already tight. Worse, users currently have to mentally cross-reference the map's "Refresh Route" total to guess, and that total is a single number for the whole day with no per-pair breakdown.

Meanwhile, the data already exists. `POST /trips/{id}/route` (`backend/app/api/endpoints/maps.py:60-191`) returns a `RouteResponse` whose `legs[]` array contains `{from_event_id, to_event_id, duration_s, distance_m}` for every consecutive routable pair (`backend/app/schemas/route.py:28-37`). The map pane fetches it (`frontend/components/map/GoogleMap.tsx:338-372`) and uses only the polyline + total — the per-leg durations are silently discarded.

## Motivation

Surfacing per-leg travel time inside the Timeline closes the loop between *time* (gap dots) and *distance* (transit). It transforms a flat list into a coachable plan: users can see at a glance that a 1h gap dot row is comfortably 12 min driving, or that a no-dot 45 min gap is already 30 min on the road. It also reuses Google data we've already paid for — the cache is keyed by waypoint tuple at 1h TTL, so repeat refreshes on an unchanged day cost $0.00.

## Fix (high level)

Stop discarding `legs[]`. Persist it in the Zustand store keyed by trip+day, then read it from the Timeline to render a small grey "clock + duration" chip in the gap area between every consecutive pair of cards on the same day. When data is missing (TBD endpoints, conflict 422, fetch error, fetch in flight) the chip is silently hidden — the existing gap dots are unaffected because they derive purely from `start_time`/`end_time`.

## Decisions (confirmed)

- **Fetch trigger**: keep the existing **explicit "Refresh Route" button** on the map pane. No auto-fetch. Timeline shows whatever was last fetched; if user edits items afterward, leg data may be stale until they refresh. This is the same staleness window the map already accepts.
- **Missing data**: hide the travel chip entirely when no leg exists; gap dots still render.
- **<1h gap**: still render the chip, plus a **single grey dot** so the chip has visual anchoring on the rail.
- **State**: extend the Zustand store with a `legsByDay: Record<dayKey, RouteLeg[]>` slice keyed by `${tripId}::${YYYY-MM-DD}`.

## Files to modify

- `frontend/lib/store.ts` — add `legsByDay` slice + `setRouteLegs(tripId, dayKey, legs)` + a small selector helper. Clear on day delete and on event delete.
- `frontend/components/map/GoogleMap.tsx` — after a successful refresh, call the new store setter with `data.legs`. The existing `routeSnapshot` local state stays — store write is additive, not a replacement.
- `frontend/components/trip/Timeline.tsx` — read legs from the store; extend the `<GapDots>` component to optionally render a `<TravelTimeChip>`; render a single-dot variant when gap < 1h but a leg exists.
- `frontend/tests/Timeline.test.tsx` — add tests for the chip render + single-dot fallback.

No backend changes. No new Google API calls. No schema changes.

## Implementation

### 1. Store slice — `frontend/lib/store.ts`

Reuse the existing `RouteLeg` shape from `GoogleMap.tsx:22` (move the type to `lib/store.ts` so both files import from one place):

```ts
export interface RouteLeg {
  from_event_id: string;
  to_event_id: string;
  duration_s: number;
  distance_m: number;
}
```

Add to the store state and actions:

```ts
// state
legsByDay: Record<string, RouteLeg[]>;  // key: `${tripId}::${YYYY-MM-DD}` — empty arrays mean "fetched, no legs"

// actions
setRouteLegs: (tripId: string, dayKey: string, legs: RouteLeg[]) => void;
clearRouteLegsForDay: (tripId: string, dayKey: string) => void;
```

Initial value: `legsByDay: {}`. Implementations:

```ts
setRouteLegs: (tripId, dayKey, legs) =>
  set((s) => ({ legsByDay: { ...s.legsByDay, [`${tripId}::${dayKey}`]: legs } })),

clearRouteLegsForDay: (tripId, dayKey) =>
  set((s) => {
    const next = { ...s.legsByDay };
    delete next[`${tripId}::${dayKey}`];
    return { legsByDay: next };
  }),
```

Invalidation hooks (so stale legs don't outlive their items):
- In `deleteTripDay` (already wipes events for the day): also `delete legsByDay[key]` for that day.
- In `removeEvent` and `moveEventToIdea`: clear the key for the affected event's `day_date` (legs reference event IDs that no longer exist).
- **Do NOT** auto-clear on `updateEventTime` or `reorderEvent` — the leg pairs are still valid (same event IDs), just possibly stale ordering. The Timeline reads them by `(from, to)` lookup, so reordering rearranges the chips correctly. Staleness is bounded by user pressing Refresh Route.

### 2. Map pane writes legs to store — `frontend/components/map/GoogleMap.tsx`

In `handleRefresh` after `data` is received (around line 372, alongside `setRouteSnapshot`), call:

```ts
const dayKey = currentDayKey;  // already computed in this file
if (tripId && dayKey) {
  useTripStore.getState().setRouteLegs(tripId, dayKey, data.legs);
}
```

Use the local `RouteLeg` type from the store (`import type { RouteLeg } from '@/lib/store'`) instead of the inline one at line 22.

### 3. Timeline reads + renders — `frontend/components/trip/Timeline.tsx`

Pull legs and build a lookup map per render:

```ts
const legsByDay = useTripStore((s) => s.legsByDay);
const dayLegs = filterDayStr && tripId ? legsByDay[`${tripId}::${filterDayStr}`] ?? null : null;
const legByPair = new Map<string, RouteLeg>();
if (dayLegs) for (const l of dayLegs) legByPair.set(`${l.from_event_id}::${l.to_event_id}`, l);
```

Add a duration formatter:

```ts
function formatTravelTime(seconds: number): string {
  const mins = Math.max(1, Math.round(seconds / 60));
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}
```

Extend `GapDots` to accept an optional `travelMinutesLabel` and an `isShortGap` flag:

```tsx
function GapDots({ count, travelLabel, isShortGap }: {
  count: number; travelLabel: string | null; isShortGap: boolean;
}) {
  if (count <= 0 && !travelLabel) return null;
  // When gap is short (<1h) but we have travel data, still render one dot.
  const dotsToRender = isShortGap && travelLabel ? 1 : count;
  return (
    <div data-testid={`gap-row-${dotsToRender}${travelLabel ? '-t' : ''}`} className="relative py-2 pl-10">
      <div className="absolute left-[17px] top-0 bottom-0 w-0.5 bg-indigo-100/60" />
      <div className="absolute flex flex-col gap-1.5" style={{ left: '15px', top: '8px' }}>
        {Array.from({ length: dotsToRender }).map((_, i) => (
          <span key={i} className={`w-1.5 h-1.5 rounded-full ${i === 0 && travelLabel ? 'bg-slate-400' : 'bg-indigo-400/70'}`} />
        ))}
      </div>
      {travelLabel && (
        <div data-testid="travel-chip" className="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-100">
          <Clock className="w-3 h-3" />
          {travelLabel}
        </div>
      )}
      <div style={{ height: `${Math.max(dotsToRender, 1) * 12 + 4}px` }} />
    </div>
  );
}
```
The first dot turns grey when a travel chip is present, anchoring the chip; the rest stay indigo. The chip sits inline at the top of the dot column, positioned in front of the first dot per the spec.

In the render map:

```ts
const prevEvent = index > 0 ? visibleEvents[index - 1] : null;
const dots = prevEvent ? gapDotCount(prevEvent, event) : 0;
const leg = prevEvent ? legByPair.get(`${prevEvent.id}::${event.id}`) : undefined;
const travelLabel = leg ? formatTravelTime(leg.duration_s) : null;
const isShortGap = !!prevEvent && dots === 0 && !!travelLabel;
// push <GapDots count={dots} travelLabel={travelLabel} isShortGap={isShortGap} />
```

### 4. Tests — `frontend/tests/Timeline.test.tsx`

Add a `describe('Timeline – travel time chip')` block. Extend `mockStore` to accept an optional `legsByDay` arg (default `{}`). Cases:

- **Chip renders for a routable pair when leg exists** (e.g., 1pm-2pm → 6pm-7pm with a 1500s leg → expect `data-testid="travel-chip"` with text `25 min`).
- **>60 min formatted as `1h 5m`** (3900s leg → "1h 5m").
- **Exactly an hour formatted as `1h`** (3600s leg → "1h").
- **No chip when leg is missing** (legs map empty, gap dots still render).
- **<1h gap renders a single grey dot + chip** when leg present (gap = 30min, leg exists → exactly one dot, chip visible).
- **<1h gap renders nothing** when leg also missing (current behavior preserved).
- **Wrong direction not matched**: a leg `(B, A)` should not be used for the rendered pair `(A, B)`.

## Verification

1. `cd frontend && npm test -- Timeline` — all existing 35 tests + new chip tests pass.
2. `cd frontend && npm run dev`:
   - Open a trip Plan page with at least 3 timed events on a single day.
   - Click "Refresh Route" on the map pane — toast shows total time as today.
   - Switch focus to Timeline — each consecutive pair now has a grey clock chip; `25 min`, `1h 5m`, etc.
   - Edit an item's time so a gap drops below 1h — verify a single grey dot + chip still appear.
   - Move an item to TBD → chip on its pair disappears (no leg has its ID).
   - Delete an item → chips on its old neighbors disappear (cleared via `removeEvent` invalidation); user re-clicks Refresh to recompute.
   - Switch to another day — chips for day 1 are not shown on day 2 (keying by day works).
3. Sanity (cost): observe in `/admin` Google Maps API usage that re-clicking Refresh on an unchanged day shows cache hits ($0).

## Out of scope

- Auto-fetch / debounced refresh on edits — explicit refresh stays the trigger.
- Walking / transit modes — backend route is driving-only today.
- Showing distance (`distance_m`) — only duration is requested.
- Backend conflict-rule alignment with the new client max-prior-end check (server uses adjacent only). If a non-adjacent conflict exists, the server may still return legs; the Timeline's red flag and the chip are independent and that's fine.
- Persisting legs across page reloads — store is in-memory; user re-clicks Refresh after reload.
