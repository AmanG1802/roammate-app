# Timeline Bin: Gap Dots + Conflict Detection Fix

## Context

Two related changes to the Timeline Bin on the trip Plan page (`frontend/components/trip/Timeline.tsx`):

1. **Gap dots (UX enhancement).** Show a vertical dot indicator between consecutive itinerary cards that visualizes idle time. Each dot = 1 floored hour of gap between previous card's `end_time` and next card's `start_time`. <1h gap → no indicator. No indicator before the first or after the last card of a day. No indicator on TBD-adjacent pairs. Recomputes naturally from rendered order — works for time edits, manual drag reorder, add/delete.

2. **Conflict detection bug fix.** `hasConflict()` currently only compares against the *immediately previous* card. It must compare against the *maximum end_time of any prior card* in the day. Example bug: order `10AM, 8PM, 2PM, 6PM` — `6PM` should be flagged (conflicts with `8PM`) but currently is not.

Both changes are pure client-side derived state — no backend, store, or schema changes. The user confirmed this scope.

## Decisions (confirmed)

- **Dot math**: `floor(gap_hours)`, no cap. Gap of 4.0h → 4 dots; 1.5h → 1 dot; 0.99h → 0 dots.
- **Conflict scope**: only the *later* item(s) in any overlap turn red (current visual behavior preserved; only the detection rule changes).
- **Manual reorder**: keep current behavior — `setEventsRaw` preserves manual order; dots and conflicts compute over rendered array order; a later time-edit re-sorts via `setEvents`/`sortEvents`. No change to drag/sort code.
- **TBD items**: skip entirely — no dots adjacent to a TBD-side gap; no red icon on TBD (already true since `start_time` is null).

## Files to modify

- `frontend/components/trip/Timeline.tsx` — only file with logic changes.
- `frontend/tests/Timeline.test.tsx` — add tests for the two new behaviors.

No store, backend, or shared util changes.

## Implementation

### 1. Replace `hasConflict` with a precomputed `conflictSet` over the day

Today (`Timeline.tsx:27-30`, used at `:283`):
```ts
function hasConflict(a: Event, b: Event): boolean {
  if (!a.end_time || !b.start_time) return false;
  return a.end_time > b.start_time;
}
// at render:
const prevEvent = index > 0 ? visibleEvents[index - 1] : null;
const isConflict = prevEvent ? hasConflict(prevEvent, event) : false;
```

Replace with a single pass that compares each timed item to the running `maxEndSoFar` across all prior timed items in `visibleEvents`:

```ts
function computeConflicts(events: Event[]): Set<string> {
  const conflicts = new Set<string>();
  let maxEndSoFar: Date | null = null;
  for (const ev of events) {
    if (ev.start_time && maxEndSoFar && ev.start_time < maxEndSoFar) {
      conflicts.add(ev.id);
    }
    if (ev.end_time && (!maxEndSoFar || ev.end_time > maxEndSoFar)) {
      maxEndSoFar = ev.end_time;
    }
  }
  return conflicts;
}
```

In the render block, compute once per render:
```ts
const conflictSet = computeConflicts(visibleEvents);
// at render of each card:
const isConflict = conflictSet.has(event.id);
```

This fixes the bug: the `10AM–1PM, 8PM–9PM, 2PM–3PM, 6PM–7PM` case marks both `2PM` and `6PM` (each `start_time` falls before `maxEndSoFar = 9PM`).

Note the strict `<` (not `≤`) preserves today's semantics — back-to-back items (`A.end == B.start`) are not a conflict.

`hasConflict` becomes unused and is deleted.

### 2. Add a `GapDots` component and render it between cards

Helper, sibling to `parseTimeString`:
```ts
function gapDotCount(prev: Event, next: Event): number {
  if (!prev.end_time || !next.start_time) return 0;
  const ms = next.start_time.getTime() - prev.end_time.getTime();
  if (ms < 60 * 60 * 1000) return 0; // <1h
  return Math.floor(ms / (60 * 60 * 1000));
}
```

Small presentational component (placed near `TimeDisplay`):
```tsx
function GapDots({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <div
      data-testid={`gap-dots-${count}`}
      aria-label={`${count} hour gap`}
      className="relative pl-10 py-1.5 flex flex-col items-center"
      style={{ marginLeft: 0 }}
    >
      <div className="absolute left-[17px] top-0 bottom-0 w-0.5 bg-indigo-100/60" />
      <div className="flex flex-col gap-1 items-center">
        {Array.from({ length: count }).map((_, i) => (
          <span key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-300/80 z-10" />
        ))}
      </div>
    </div>
  );
}
```
The absolute spine matches the existing `before:left-[17px]` rail on the timeline container (`Timeline.tsx:279`), so dots sit on the spine, in line with the category dots on each card.

In the map at `Timeline.tsx:281`, render a `GapDots` *before* each non-first card based on the prior visible event:

```tsx
{visibleEvents.map((event, index) => {
  const prevEvent = index > 0 ? visibleEvents[index - 1] : null;
  const dots = prevEvent ? gapDotCount(prevEvent, event) : 0;
  const isConflict = conflictSet.has(event.id);
  // ...
  return (
    <Fragment key={event.id}>
      {dots > 0 && <GapDots count={dots} />}
      <motion.div /* existing card */>...</motion.div>
    </Fragment>
  );
})}
```
Import `Fragment` from `react`. Because `GapDots` only renders when `dots > 0` and `index > 0`, it never appears before the first item or after the last; an empty day shows no dots (the empty-state branch at `:263` is unchanged).

### 3. Tests (`frontend/tests/Timeline.test.tsx`)

Add two test groups, mirroring existing patterns in the file:

- **Non-adjacent conflict**: render events `10–13`, `20–21`, `14–15`, `18–19` (in that array order). Assert `data-testid="conflict-icon"` appears on the cards for `14–15` and `18–19`, and not on `10–13` or `20–21`.
- **Gap dots**:
  - 1pm–2pm then 6pm–7pm → `data-testid="gap-dots-4"` present.
  - 1pm–2pm then 2:30pm–3pm → no `gap-dots-*` element.
  - First card has no preceding `gap-dots-*`.
  - TBD next to a timed card → no dots.
  - Empty day → no dots.

## Verification

1. `cd frontend && npm test -- Timeline` — new + existing tests pass.
2. `cd frontend && npm run dev`, open a trip Plan page:
   - Add three items to a single day at 10am–11am, 12pm–1pm, 5pm–6pm. Expect 0 dots between #1–#2 (1h exact → 1 dot — wait: 11→12 = 1h → `floor(1)=1` → 1 dot) and 4 dots between #2–#3.
   - Edit times to create non-adjacent overlap (e.g. `10–13, 20–21, 14, 18`); verify both `14` and `18` cards turn red.
   - Drag-reorder cards; verify dots and red flags recompute on the new rendered order.
   - Delete a card; verify dots between the new neighbors recompute.
   - Add a new empty day; verify no dots render in its empty-state.
3. Sanity: existing concierge (`readOnly`) mode still renders correctly — `GapDots` is rendered identically in both modes since it sits outside the card.

## Out of scope (explicitly not changing)

- `sortEvents` / `setEvents` / `setEventsRaw` semantics in `lib/store.ts`.
- The drag-reorder insertion logic in `handleEventDrop` (`Timeline.tsx:201-240`).
- Backend `events.py` and the `Event` model.
- The "modify time auto re-orders" behavior — already correct via `updateEventTime → sortEvents`.
