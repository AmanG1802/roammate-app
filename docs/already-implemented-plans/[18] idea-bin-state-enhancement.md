# IdeaBin State Enhancement

## Problem

When navigating back to the Plan page, Idea Bin cards appear immediately but show no category badge, rating, or accent color for ~0.5s. This is caused by a split between two separate state containers that are both populated from the same API response.

### The split

**`ideas[]`** (id, title, lat, lng, place_id, start_time, votes) → lives in **Zustand store**. Persists across SPA navigations.

**`extras`** (category, photo_url, rating, address, description) → lives in **local `useState`** in `IdeaBin.tsx:67`. Resets to `{}` on every component mount.

### Render sequence on page navigation

```
1. IdeaBin mounts
   → Zustand already has ideas[] from previous visit
   → extras = {} (reset)
   → Cards render immediately: titles visible, but
     extras[idea.id] is undefined → category shows "—",
     no accent color, no rating

2. loadIdeas() fires (async fetch to /trips/{tripId}/ideas)
   → ~0.5s network round trip

3. Fetch resolves → setIdeas() + setExtras() called together
   → extras populated → category, rating, colors appear
```

### Secondary issue: start_time deserialization

`start_time` is stored as a `Date` object in Zustand. JavaScript serialization (e.g. structuredClone or JSON round-trip) converts it to a string. `formatTime()` receives a string, not a `Date`, and returns `"No time"` until `loadIdeas()` re-runs `new Date(item.start_time)`.

---

## Timeline: Same Issue?

**No.** The `Event` interface in `lib/store.ts` already includes all enrichment fields directly:

```ts
export interface Event {
  // ...
  category?: string | null;
  description?: string | null;
  photo_url?: string | null;
  rating?: number | null;
  address?: string | null;
  place_id?: string | null;
}
```

Timeline renders all fields directly from Zustand with no local extras split. The fix to apply is exactly what Timeline already does — merge enrichment fields into the Zustand item type.

---

## Fix

Remove the `extras` local state entirely and extend `IdeaBinItem` in Zustand to hold all enrichment fields. Since both `ideas` and `extras` are populated from the same single API call, there is no reason for the split.

### 1. Extend `IdeaBinItem` in `frontend/lib/store.ts`

```ts
export interface IdeaBinItem {
  id: string;
  title: string;
  lat: number;
  lng: number;
  place_id?: string | null;
  start_time: Date | null;
  end_time: Date | null;
  added_by?: string | null;
  up?: number;
  down?: number;
  my_vote?: number;
  // Add these:
  category?: string | null;
  photo_url?: string | null;
  rating?: number | null;
  address?: string | null;
  description?: string | null;
}
```

### 2. Remove `extras` state from `frontend/components/trip/IdeaBin.tsx`

Remove line 67:
```ts
// DELETE this line:
const [extras, setExtras] = useState<Record<string, { ... }>>({});
```

### 3. Inline enrichment fields into `setIdeas()` in `loadIdeas()`

In the `data.map()` inside `loadIdeas()` (lines 105-127), add:
```ts
category: item.category ?? null,
photo_url: item.photo_url ?? null,
rating: item.rating ?? null,
address: item.address ?? null,
description: item.description ?? null,
```

Remove the `extraMap` block (lines 128-138) and the `setExtras(extraMap)` call.

### 4. Update all render references

Replace every `extras[idea.id]?.X` reference with `idea.X`:

| Old | New |
|-----|-----|
| `categoryAccent(extras[idea.id]?.category)` | `categoryAccent(idea.category)` |
| `extras[idea.id]?.rating` | `idea.rating` |
| `extras[idea.id]?.category` | `idea.category` |
| `extras[idea.id]?.photo_url` | `idea.photo_url` |
| `extras[idea.id]?.description` | `idea.description` |
| `extras[idea.id]?.address` | `idea.address` |

The detail popover (`openId` section, lines 439-505) also reads from `extras` — update those references too.

---

## Result

All idea data lives in Zustand. On SPA navigation back to the Plan page, the store already has fully-enriched idea objects. Cards render immediately with category badge, accent color, and rating. No flash.
