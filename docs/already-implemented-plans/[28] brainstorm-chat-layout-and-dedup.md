# Brainstorm Chat — Layout cleanup + re-extraction dedup

## Context

The Brainstorm Chat screen has two problems:

1. **Layout is cluttered and inconsistent.** The "Extract ideas from chat" capsule and the "15/15 left" quota pill stack awkwardly above the input — centered button + right-aligned pill on different lines. When the extract button is hidden (manual trip, or Plan Trip flow that already populated the bin), only the quota pill remains, which looks orphaned. There is also no clear in-screen affordance when the quota is exhausted.

2. **Re-extracting from chat re-creates already-extracted items.** After items get promoted from the brainstorm bin to the itinerary (or trashed), the bin is empty. The `/brainstorm/extract` endpoint re-feeds the entire chat history to the LLM and deduplicates only against the current bin contents — so the same ideas get re-generated and re-inserted into the bin.

Goal: ship a layout that scales across all chat states (quota>0/no-extract, quota>0/extract-shown, quota=0) consistently on iOS and web, plus fix the dedup root cause by tracking which chat messages have already been extracted.

## Approach

### Part 1 — Layout (iOS + web)

**Pattern: quota pill in chat header, extract as inline CTA above input.**

- **Quota pill** lives permanently in the chat screen's top header, right of the title, left of the menu icon. Always visible while the chat is open.
- **Extract button** appears as a full-width prominent CTA directly above the text input, only when the conditions for extraction are met (existing `hasAssistant` / `store.messages.count >= 2`).
- **Quota = 0 state:**
  - Header pill swaps to a danger-toned "Get Plus" chip → tap opens the paywall (`PaywallFeature.brainstormQuota`).
  - Send button is replaced by a lock icon button → tap also opens the paywall. The text input is disabled.
  - Extract button is hidden (extract is also gated by the same quota).

### Part 2 — Re-extraction dedup

Add an `extracted_at` timestamp column to `BrainstormMessage`. The extract endpoint only feeds messages where `extracted_at IS NULL` to the LLM, then stamps them on success. New chat turns are the only source of new items — fully decoupled from bin contents.

- If there are no unextracted messages on click, return an empty result (no LLM call, no counter tick).
- Existing bin-contents dedup (`deduplicate(raw_items, existing_rows)`) stays as a belt-and-braces guard against the LLM re-suggesting something already visible.
- `BrainstormMessage` is a single `Base.metadata.create_all`-managed table; the auto_migrate helper at `backend/app/db/auto_migrate.py` will add the nullable column on next boot — no Alembic migration needed.

## Files to change

### Backend

- `backend/app/models/all_models.py` — add `extracted_at = Column(DateTime(timezone=True), nullable=True, index=True)` to `BrainstormMessage` (~L163).
- `backend/app/api/endpoints/brainstorm.py` — in `extract` (~L251):
  - Restrict the `BrainstormMessage` query to rows where `extracted_at IS NULL` (still ordered by `created_at`).
  - If no unextracted rows → return `BrainstormExtractResponse(items=[], enrichment=None)` early, **before** the LLM call and **before** `bump_brainstorm_counter`.
  - After LLM + enrichment + insert succeed, stamp the consumed rows: `UPDATE brainstorm_message SET extracted_at = now() WHERE id IN (...)` in the same transaction as the bin inserts.
- Keep the existing `deduplicate(raw_items, existing_rows)` call as-is.

### iOS

- `ios/Roammate/Views/Trips/Brainstorm/BrainstormChatView.swift`
  - Remove the in-body `quotaPill` view from below the extract button.
  - Promote the extract button to a full-width prominent capsule (gradient indigo/violet to match web), tighten vertical padding around it.
  - At `brainstormRemaining == 0`: hide the extract button; replace send button with a lock icon button that posts `.needsPlus`; disable the text field.
- The screen's host header (where "Pune Brews & Heritage" + menu live — locate via `BrainstormPaneView` / its enclosing `NavigationStack`/toolbar) needs a new top-right `quotaPill` toolbar item. Reuse the existing `QuotaTone` styling. Tap at zero remaining posts `.needsPlus`.

### Web

- `frontend/components/trip/BrainstormChat.tsx`
  - Remove the `<BrainstormQuotaPill />` placement (~L268) from the input area.
  - Mount the quota pill in the chat screen's header (find the wrapping page/header component that renders the title — likely in `app/(trips)/trips/[tripId]/...` or a `TripHeader` component; place it next to the menu icon, right-aligned).
  - At quota = 0: hide the extract button; replace the send icon with a lock icon button that opens the paywall modal; disable the textarea.
- `frontend/components/billing/QuotaPill.tsx` — extend to accept a `variant="header"` so it can render compact next to the title; or render a sibling "Get Plus" chip when `remaining === 0` that opens the paywall.

## Verification

1. **Backend unit test** (or REPL): create a trip with two chat turns, call `/brainstorm/extract` → expect items created and both messages stamped with `extracted_at`. Promote all items (bin empty). Call `/brainstorm/extract` again with no new chat → expect `items: []`, no counter tick, no DB inserts. Send one new user+assistant turn; call extract → expect items only from the new turn.
2. **iOS**: run on simulator. Manual trip → open Brainstorm pane → confirm header pill visible, no extract button, send works. Send a message + get reply → extract button appears above input → tap → items go to bin. Promote them. Chat one new turn → tap extract → only the new item appears (not the older ones).
3. **iOS quota = 0**: temporarily seed entitlement with `brainstormRemaining = 0` → confirm header pill becomes red "Get Plus", send button becomes lock, both open the paywall.
4. **Web**: mirror steps 2–3 in `frontend/` against the dev server.
5. **Smoke**: confirm Plan Trip → bulk insert path is unaffected (it doesn't touch `BrainstormMessage`, so `extracted_at` is irrelevant there).

## Critical files referenced

- `backend/app/api/endpoints/brainstorm.py:251` — extract endpoint
- `backend/app/models/all_models.py:163` — `BrainstormMessage` model
- `backend/app/db/auto_migrate.py` — handles the new nullable column
- `backend/app/services/llm/dedup.py` — keep as secondary guard
- `ios/Roammate/Views/Trips/Brainstorm/BrainstormChatView.swift:179` — extract button + quota pill
- `ios/Roammate/Views/Trips/Brainstorm/BrainstormPaneView.swift` — pane container (header lives in its parent)
- `frontend/components/trip/BrainstormChat.tsx:265` — input area
- `frontend/components/billing/QuotaPill.tsx` — pill component
