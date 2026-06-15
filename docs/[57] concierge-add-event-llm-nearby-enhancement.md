# [57] Concierge `add_event` — LLM + Nearby Search Enhancement

## Context

Plan [56] fixes the immediate enrichment bug: `add_event` params are hydrated with
`find_place()` before the action card is shown, so created events have coordinates and
participate in route rendering.

This plan addresses the deeper UX problem: when a user says *"add a coffee stop at 10am
tomorrow"*, the current flow picks **one** place (whatever `find_place` returns first)
and commits it after a single confirmation. The user has no agency over which specific
place is added. The `find_nearby → selectPlace` flow already solves this — it shows a
carousel of options and lets the user pick — but it requires the user to explicitly say
"find nearby". This plan unifies the two so that `add_event` from natural language also
gives the user a selection.

---

## Problem statement

| Flow | UX | Place selection | Enriched? |
|---|---|---|---|
| `find_nearby` → `selectPlace` | User picks from carousel | ✓ Full choice | ✓ Yes |
| `add_event` (current, post-plan-56) | Auto-confirms first `find_place` result | ✗ No choice | ✓ Yes (bug fixed) |
| Ideal | Natural language → pick from options → confirm | ✓ Full choice | ✓ Yes |

The gap: `add_event` from natural language should trigger a nearby-search carousel
rather than silently picking the first result.

---

## Ideas and approaches

### Approach A — Intent reclassification: `add_event` → `find_nearby` when place is ambiguous

**How it works:**
- LLM dispatches `add_event` with `title` and `start_time` (as today).
- Backend detects the params lack a `place_id` (i.e., it's an ambiguous place name).
- Instead of calling `find_place` silently, the executor calls `nearby_search` with the
  title as query.
- Returns a `find_nearby` card (place carousel) with `start_time` attached to each
  result as metadata.
- User selects a place → `selectPlace()` fires → `add_event` executes with full
  enrichment and the pre-filled time.

**Pros:**
- Reuses the already-built `find_nearby → selectPlace` pipeline end-to-end.
- No new UI components needed.
- User gets choice every time.

**Cons:**
- Conflates two intents. A user saying "add dinner at Luigi's Restaurant" (a specific
  named place) still gets a carousel — feels like extra friction when the intent is
  clear.
- `start_time` must be threaded through the carousel → `selectPlace` call, which
  currently doesn't carry a time.

---

### Approach B — Per-intent prompts with a new `add_event_search` intent

**How it works:**
- Add a new intent: `add_event_search` ("the user wants to add an activity but hasn't
  picked a specific venue").
- Separate the LLM's job into two prompts:
  - **Dispatch prompt** (existing): classify intent from the message.
  - **Add-event prompt** (new): for `add_event`/`add_event_search` intents, extract
    `title`, `start_time`, `duration_hint`, `category`, `day_date`.
- When intent = `add_event_search`, backend runs `nearby_search` and returns a carousel.
- When intent = `add_event` (specific named place), backend runs `find_place` silently
  (plan 56 behavior).

**Pros:**
- Clean semantic split. The LLM is explicitly asked to distinguish "I want a coffee
  shop" from "Add Café Bloom at 10am".
- Per-intent prompts are smaller and more accurate than a monolithic dispatch prompt.
- Aligns with the broader prompt-per-intent migration.

**Cons:**
- Requires a new intent in schema, new prompt file, and updated iOS/web model.
- More LLM calls per message (dispatch → then per-intent extraction).
- Prompt-per-intent migration is a larger refactor; doing it piecemeal may create
  inconsistency.

---

### Approach C — Hybrid: always show carousel for ambiguous places, silent for exact matches

**How it works:**
- Use the dispatch prompt to classify intent as `add_event` with a new boolean param
  `is_named_place: bool` (LLM decides: is "coffee shop" ambiguous → false; "Café Bloom"
  → true).
- If `is_named_place = true`: run `find_place`, enrich silently, show action card.
- If `is_named_place = false`: run `nearby_search`, return carousel.
- Same executor, branching on the param.

**Pros:**
- Single intent, single prompt. Small delta from today's state.
- Correct friction: specific place → quick confirm; vague place → pick from options.

**Cons:**
- LLM judgment on `is_named_place` may be unreliable (edge cases: "that sushi place we
  saw" is ambiguous but reads like a named reference).
- Adds branching to `_add()` that may be hard to test exhaustively.

---

## Recommendation

**Approach B (per-intent prompts + `add_event_search` intent)**, implemented in two
phases:

**Phase 1** (this plan, shorter scope):
- Add `add_event_search` intent.
- Update dispatch prompt to emit it when the place is a category/vague description.
- In executor: `add_event_search` runs `nearby_search` and returns a place carousel
  with `start_time` attached per result.
- Update `selectPlace()` on iOS/web to accept and pre-fill `start_time` from carousel
  metadata.

**Phase 2** (follow-up):
- Migrate remaining intents to per-intent extraction prompts (smaller, faster, more
  accurate).
- Replace the monolithic `concierge_dispatch_v1.txt` with a two-step
  classify → extract pipeline.

---

## What needs answering before building

1. **`selectPlace()` time threading**: currently `selectPlace` in `ConciergeStore.swift`
   constructs the `add_event` params from the place object. Where should `start_time`
   live — in the place carousel item metadata, or in a separate context stored on the
   store?

2. **Carousel title**: when the carousel originates from an `add_event_search`, should
   the intro text say *"Here are some options for your coffee stop at 10am"* (combining
   the query + time)? Who writes this — the LLM or a template?

3. **Fallback**: if `nearby_search` returns 0 results (obscure location, poor coverage),
   fall back to `find_place` silently, or return an error asking the user to be more
   specific?

4. **Prompt migration sequencing**: do we want to ship Phase 1 (`add_event_search`)
   before the broader prompt-per-intent refactor, or gate it on the refactor completing?

---

## Scope explicitly excluded

- Per-intent prompt migration (Phase 2 above) — separate plan.
- Cross-day move via `add_event` — covered in Plan [56] future scope section.
- Web `selectPlace` changes — covered in the same implementation milestone as iOS.
