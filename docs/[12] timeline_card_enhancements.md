---
name: Timeline Card Enhancements
overview: "Restructure the timeline event card layout in Timeline.tsx to fix category/details wrapping, show both start and end times inline, reposition elements for better information hierarchy, and center-align travel hints. ALL DONE — staged on branch aman/timeline-bin-polishing."
todos:
  - id: card-layout
    content: "Restructure the card JSX in Timeline.tsx: 4-row layout (Title, Time+MoveToBin, Category+Details+Votes), remove right column, move VoteControl inline with Details row"
    status: completed
  - id: time-display
    content: "Modify TimeDisplay to show start–end time range inline on badge; add click-outside dismiss and isDirty guard to TimeEditor; compact badge and editor sizing"
    status: completed
  - id: center-hint
    content: Center-align the travel hint text under the card
    status: completed
  - id: update-tests
    content: "Update Timeline.test.tsx: start+end badge, start-only fallback, editor DOM ordering, vote visibility with details open, travel hint centering"
    status: completed
  - id: commit
    content: "Commit staged changes on aman/timeline-bin-polishing"
    status: pending
isProject: false
---

# Timeline Card Layout Enhancements

## Current State

The card currently uses a two-column layout (lines 400-478 of [Timeline.tsx](frontend/components/trip/Timeline.tsx)):

- **Left column**: grip icon, title (truncated), then a `flex-wrap` row containing the category badge + Details button
- **Right column**: time badge (start only) + "Move to bin" button
- **Below the card**: voting buttons (right-aligned), then the travel hint (left-aligned)

**Problems visible in the screenshot:**
1. "RELIGIOUS & SPIRITUAL" is so wide that the Details button wraps to a second line, while shorter categories like "SHOPPING" keep Details inline -- inconsistent visual rhythm.
2. Only start time is shown ("10:00 AM"). End time is buried inside the Details tooltip, giving users no quick sense of how long an activity lasts.
3. The title "Chatuchak Weeken..." is truncated because the right column (time + Move to bin) eats horizontal space.
4. "20 min drive to next destination" is left-aligned relative to the card padding, not centered.

---

## Enhancement 1 -- Consistent Category and Details Rows

**What:** Break the current `flex-wrap` row (category + Details on the same line) into two separate stacked lines -- category on its own line, Details button always on the next line.

**Why:** When long category strings like "RELIGIOUS & SPIRITUAL" share a row with the Details button, the button wraps unpredictably. Some cards show them side-by-side, others stack them -- this inconsistency looks unpolished. Giving each its own line means every card has the same visual cadence regardless of category length.

**How:** In [Timeline.tsx](frontend/components/trip/Timeline.tsx) lines 409-434, replace the single `flex items-center gap-1.5 mt-1.5 flex-wrap` container with two separate rows:
- Row 1: category badge only
- Row 2: Details button + voting buttons (see Enhancement 2)

---

## Enhancement 2 -- Restructured Card Layout (4 Rows)

**What:** Reorganize the card into a clean 4-line vertical layout with repositioned elements:

```
Row 1:  [grip] Title
Row 2:  10:00 AM - 12:00 PM                     [Move to bin]
Row 3:  RELIGIOUS & SPIRITUAL
Row 4:  (i) Details                              [👍 0] [👎 0]
```

**Why this is better UX:**
- **Title gets the full width** -- no more truncation from the time badge stealing right-column space. "Chatuchak Weekend Market" will display fully.
- **Start + end time visible at a glance** -- users immediately know the duration (e.g., "10:00 AM - 12:00 PM" = 2 hours) without clicking Details. This is critical for itinerary planning.
- **Move to bin repositioned** to the end of the time row (right-aligned), which is a natural secondary-action position and frees the title row.
- **Voting stays inline with Details** on the last row -- they are both engagement actions, so grouping them makes sense. They remain in place when Details is expanded.

**Key implementation details in [Timeline.tsx](frontend/components/trip/Timeline.tsx):**

1. **Row 1 (Title)** -- Remove the right-column `<div>` that currently holds time + move-to-bin (lines 439-478). Title gets `flex-1 min-w-0` with no competing right element, so `truncate` can be removed or the threshold increases significantly.

2. **Row 2 (Time + Move to bin)** -- Create a new `flex justify-between items-center` row:
   - Left: show `format(start_time, 'h:mm a')` + separator + `format(end_time, 'h:mm a')` as a text span (not a badge). If only start exists, show just start. If TBD, show TBD badge. The pencil icon to edit stays next to the time text.
   - Right: "Move to bin" button (always visible, not just on hover -- since it now lives on its own row there's space).
   - Keep `TimeDisplay` and `TimeEditor` components, but modify `TimeDisplay` to show the range.

3. **Row 3 (Category)** -- Category badge on its own line, no `flex-wrap` needed.

4. **Row 4 (Details + Votes)** -- `flex justify-between items-center`:
   - Left: Details toggle button
   - Right: `VoteControl` component (moved here from its current separate `mt-2 flex justify-end` wrapper at line 542)

5. **Time editor placement** -- When the user clicks the pencil icon, the `TimeEditor` renders immediately below Row 2 (between time row and category row), pushing Rows 3-4 down. On confirm/cancel, it collapses and rows return to normal. This is already how AnimatePresence works, just needs the editor insertion point moved to right after Row 2 instead of after the entire card body (current line 530-540).

6. **Details expansion** -- When the user clicks Details, the expandable panel still renders at the bottom of the card (after Row 4). Voting buttons stay on Row 4 and do not move. The card simply grows taller. This is already the current behavior with `AnimatePresence` at line 482; it just stays in place.

7. **Photo in details** -- The `SHOW_PHOTOS` flag already conditionally renders `event.photo_url` inside the detail panel (line 492-497). No change needed -- the new layout does not affect the expanded panel's internal structure.

8. **Read-only mode** -- When `readOnly` is true, the time row hides the pencil and Move to bin. The grip icon is already conditionally hidden (line 403). The time still displays as a static range.

---

## Enhancement 3 -- Center-Aligned Travel Hint

**What:** Center the "20 min drive to next destination" text relative to the card width.

**Why:** Left-aligned hints look orphaned under the card. Centering them makes the hint feel like a connector between two cards rather than metadata attached to the top card.

**How:** In [Timeline.tsx](frontend/components/trip/Timeline.tsx) line 548-554, change the `<p>` from `ml-1 text-left` alignment to `text-center` and remove `ml-1`. The hint sits outside the card `<div>` but inside the `pl-10` wrapper, so centering within that wrapper aligns it with the card's visual center.

```tsx
<p
  data-testid={`travel-hint-${event.id}`}
  className="mt-1.5 text-center text-[11px] italic text-slate-400 font-medium"
>
```

---

## Test Updates ([Timeline.test.tsx](frontend/tests/Timeline.test.tsx))

- Update existing time-badge tests to verify both start and end time are rendered in the card body (not just start).
- Add a test that the time editor appears between the time row and category row (DOM ordering).
- Add a test that voting buttons remain visible when Details panel is open.
- Add a test that the travel hint has `text-center` class (or visually verify centering).
- Existing drag, conflict, gap-dot, and travel-hint tests should remain unchanged since the card's `data-testid` attributes are preserved.

---

## Files to Change

| File | Scope |
|------|-------|
| `frontend/components/trip/Timeline.tsx` | Restructure card JSX, modify `TimeDisplay`, reposition `VoteControl`, center travel hint |
| `frontend/tests/Timeline.test.tsx` | Update assertions for new layout structure |

No backend changes, no new dependencies, no store changes.
