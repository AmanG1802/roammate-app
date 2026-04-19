# Plan: Brainstorm Section + Dashboard Trip-Planning Chatbox

## Context

Before starting Phase 1A (LLM intelligence) and Phase 1B (spatial/timeboxing), we're adding a thin LLM-facing surface so the product has a visible AI touchpoint even while the real LLM integration is deferred. Two user-facing features:

1. **Per-trip "Brainstorm" section** — a new left-menu entry (placed *before* Plan) opening a split-pane: left = chat with LLM about the destination, right = "Brainstorm Bin" holding discovered places/activities. Users curate the brainstorm output by clicking "Select" (border-highlight selection) or "Add All", then promote to the Idea Bin. Promotion is one-way and **moves** items (removes from Brainstorm).

2. **Dashboard single-prompt trip planner** — a chatbox above the Today Widget carousel. User types a free-form prompt ("5-day Thailand itinerary…"), clicks **"Create Trip and Take Me There"**, and the system auto-creates a Trip and seeds its Brainstorm Bin with AI-generated items. The Trip landing page also gets a "Go to Brainstorm" CTA.

Because the real LLM keys aren't wired yet, a new `llm_client.py` module ships with a `LLM_ENABLED=False` flag. When disabled, every call returns a hardcoded Thailand-Bangkok payload (3-day trip, 6 Bangkok places).

**Decisions locked:**
- **Brainstorm is per-user-per-trip.** Each trip member has their own private Brainstorm chat + Brainstorm Bin. Alice's brainstorming is invisible to Bob even though they're both on the same trip. This keeps brainstorming a personal ideation space; the shared artifact is the Idea Bin.
- **Promotion = move** (delete from Brainstorm after promotion).
- **Chat history persists per-trip-per-user** in DB (multi-turn context server-side).
- **Dashboard-generated items** seed the creator's Brainstorm Bin on the new trip (never skip to Idea Bin).
- **Brainstorm → Idea Bin**: open to any trip member (chat is theirs; the items they surface are theirs to share). **Idea Bin → Timeline**: stays admin-only (unchanged from current behavior).
- **Promotion copies every field** on the Brainstorm item 1:1 into the Idea Bin item. The LLM is expected to populate rich Google-Maps-ready fields (address, rating, photo_url, opening_hours, etc.) — these carry through. Voting fields unlock at the Idea Bin level.
- **`added_by` on the promoted Idea Bin item** = the user who triggered the promotion (first name), **not "AI"**. Brainstorm items themselves record the LLM/user who created them.
- Brainstorm items are **not votable/taggable** in the Brainstorm Bin; voting & tags activate only once promoted into the Idea Bin.

---

## Architecture Overview

```
Dashboard Chatbox ──► POST /api/llm/plan-trip ──► llm_client.plan_trip()
       │                                            │
       └─ "Create Trip" ──► POST /api/trips/ ──► POST /api/trips/{id}/brainstorm/bulk
                                                    │
Brainstorm UI ◄──────────────────────────────────── DB (BrainstormBinItem)
   │                                                     ▲
   ├─ chat ──► POST /api/trips/{id}/brainstorm/chat ──► llm_client.chat()
   │                                                     │
   ├─ "Create items from chat" ──► POST .../brainstorm/extract ──► llm_client.extract_items()
   │
   └─ "Promote to Idea Bin" ──► POST .../brainstorm/promote (move-semantics)
                                                    │
                                        IdeaBinItem (existing) ◄── copy then delete from Brainstorm
```

---

## Backend Changes

### 1. New DB models — `backend/app/models/all_models.py`

```python
class BrainstormBinItem(Base):
    __tablename__ = "brainstorm_bin_items"
    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)  # owner
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)         # 1–2 sentence blurb from LLM
    category = Column(String, nullable=True)          # "restaurant" | "sight" | "activity" | "neighborhood"
    # Google Maps / Places fields (LLM pre-populates; real Maps enrichment in Phase 1B will refresh)
    place_id = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    price_level = Column(Integer, nullable=True)      # 0–4 per Google convention
    types = Column(JSON, nullable=True)               # list of Google "types" strings
    opening_hours = Column(JSON, nullable=True)       # structured; opaque to us until 1B
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    # UX / provenance
    time_hint = Column(String, nullable=True)         # optional — the LLM may suggest "morning", "2pm", etc.
    url_source = Column(String, nullable=True)        # source URL if scraped
    added_by = Column(String, nullable=True)          # "AI" when LLM-generated, or user first name when manually added
    created_at = Column(DateTime, default=datetime.utcnow)
    trip = relationship("Trip", back_populates="brainstorm_bin_items")
    user = relationship("User")

class BrainstormMessage(Base):
    __tablename__ = "brainstorm_messages"
    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)  # owner
    role = Column(String, nullable=False)             # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    trip = relationship("Trip", back_populates="brainstorm_messages")
    user = relationship("User")
```

**Per-user scoping:** every query in the brainstorm endpoints filters by both `trip_id` *and* `user_id=current_user.id`. Two members on the same trip each see only their own bin + chat.

**IdeaBinItem parity:** to allow field-for-field promotion, `IdeaBinItem` must gain the same new columns (`description`, `category`, `address`, `photo_url`, `rating`, `price_level`, `types`, `opening_hours`, `phone`, `website`). `auto_migrate.py` will add them on startup via `ALTER TABLE … ADD COLUMN IF NOT EXISTS`. Existing rows get NULLs — no backfill needed. Update `IdeaBinItemBase` / `IdeaBinItem` Pydantic schemas in `backend/app/schemas/trip.py` to expose the new fields in responses; all new fields are `Optional`, so existing clients keep working.

Add reverse relationships on `Trip`:
```python
brainstorm_bin_items = relationship("BrainstormBinItem", back_populates="trip", cascade="all, delete-orphan")
brainstorm_messages = relationship("BrainstormMessage", back_populates="trip", cascade="all, delete-orphan")
```

**Migration:** None — `app/db/auto_migrate.py` diffs SQLAlchemy metadata against live Postgres on startup and auto-creates new tables/columns. Test suite uses in-memory SQLite with `Base.metadata.create_all`, which picks up new tables automatically.

### 2. New Pydantic schemas — `backend/app/schemas/brainstorm.py` (new file)

```python
class BrainstormItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    place_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None
    price_level: Optional[int] = None
    types: Optional[List[str]] = None
    opening_hours: Optional[dict] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    time_hint: Optional[str] = None
    url_source: Optional[str] = None

class BrainstormItemCreate(BrainstormItemBase): pass

class BrainstormItemOut(BrainstormItemBase):
    id: int
    trip_id: int
    user_id: int
    added_by: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BrainstormMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BrainstormChatRequest(BaseModel):
    message: str

class BrainstormChatResponse(BaseModel):
    assistant_message: BrainstormMessageOut
    history: List[BrainstormMessageOut]             # full running history

class BrainstormExtractResponse(BaseModel):
    items: List[BrainstormItemOut]                  # newly created items

class BrainstormPromoteRequest(BaseModel):
    item_ids: Optional[List[int]] = None            # None => promote all
    
class PlanTripRequest(BaseModel):
    prompt: str

class PlanTripResponse(BaseModel):
    trip_name: str
    start_date: Optional[datetime]
    duration_days: int
    items: List[BrainstormItemBase]                 # preview; not yet persisted
```

### 3. New service — `backend/app/services/llm_client.py` (new file)

```python
LLM_ENABLED = settings.LLM_ENABLED   # default False

_BANGKOK_FALLBACK_ITEMS = [
    # Each item is fully populated — title, description, category, place_id, lat, lng,
    # address, photo_url, rating, price_level, types, opening_hours, phone, website.
    # These are realistic placeholder values that mirror what Google Places will return in Phase 1B.
    {"title": "Grand Palace", "description": "...", "category": "sight",
     "place_id": "ChIJ...", "lat": 13.7500, "lng": 100.4913,
     "address": "Na Phra Lan Rd, Bangkok 10200", "photo_url": "...",
     "rating": 4.7, "price_level": 2, "types": ["tourist_attraction", "point_of_interest"],
     "opening_hours": {"mon_fri": "8:30–15:30", "weekend": "8:30–15:30"},
     "phone": None, "website": "https://www.royalgrandpalace.th/"},
    {"title": "Wat Arun", ...},
    {"title": "Chatuchak Weekend Market", ...},
    {"title": "Lumphini Park", ...},
    {"title": "Chinatown (Yaowarat)", ...},
    {"title": "Jim Thompson House", ...},
]

_THAILAND_PLAN_FALLBACK = {
    "trip_name": "Thailand Getaway",
    "start_date": None,                              # user fills in; or today+14
    "duration_days": 3,
    "items": _BANGKOK_FALLBACK_ITEMS,
}

async def chat(history: list[dict], user_message: str) -> str:
    if not LLM_ENABLED:
        return "Here are some great spots in Bangkok you might like: Grand Palace, Wat Arun, Chatuchak Market, Lumphini Park, Chinatown, and Jim Thompson House."
    # real LLM call (deferred to Phase 1A)

async def extract_items(history: list[dict]) -> list[dict]:
    if not LLM_ENABLED:
        return _BANGKOK_FALLBACK_ITEMS
    # real LLM call

async def plan_trip(prompt: str) -> dict:
    if not LLM_ENABLED:
        return _THAILAND_PLAN_FALLBACK
    # real LLM call
```

Add `LLM_ENABLED: bool = False` to `app/core/config.py` Settings.

### 4. New endpoints module — `backend/app/api/endpoints/brainstorm.py` (new file)

All endpoints go through `require_trip_member` / `require_trip_admin` gating (reusing `app/services/roles.py`).

All endpoints require `require_trip_member` only. Every DB query additionally filters by `user_id == current_user.id` so one member can never see or mutate another member's brainstorm data.

| Method | Path | Gating | Purpose |
|---|---|---|---|
| `GET` | `/api/trips/{trip_id}/brainstorm/items` | member + user-scoped | List the caller's brainstorm bin |
| `GET` | `/api/trips/{trip_id}/brainstorm/messages` | member + user-scoped | Caller's chat history |
| `POST` | `/api/trips/{trip_id}/brainstorm/chat` | member + user-scoped | Append user msg, call `llm_client.chat` with caller's history, persist assistant msg, return both |
| `POST` | `/api/trips/{trip_id}/brainstorm/extract` | member + user-scoped | Read caller's chat history → `llm_client.extract_items` → persist owned by caller + return items |
| `POST` | `/api/trips/{trip_id}/brainstorm/bulk` | member + user-scoped | Bulk-insert items into caller's bin (used by Dashboard create-trip flow). Body: `{items: [BrainstormItemBase]}` |
| `POST` | `/api/trips/{trip_id}/brainstorm/promote` | member + user-scoped | Move caller's items → shared IdeaBinItem. Body: `{item_ids: [...] or null}`. Returns the created `IdeaBinItem`s. |
| `DELETE` | `/api/trips/{trip_id}/brainstorm/items/{item_id}` | member + user-scoped (must own item) | Remove a single brainstorm item from caller's bin |

**Promotion mapping (brainstorm → idea) — full copy:**

Every field present on `BrainstormBinItem` copies 1:1 to the new `IdeaBinItem` (after the `IdeaBinItem` schema-extension described above):
- `title`, `description`, `category`
- `place_id`, `lat`, `lng`, `address`, `photo_url`, `rating`, `price_level`, `types`, `opening_hours`, `phone`, `website`
- `time_hint`, `url_source`

**`added_by` on the promoted row = the promoting user's first name** (from `current_user.first_name`) — never "AI", regardless of how the brainstorm item originated. The chain-of-custody is preserved: the user who decides to share an idea with the trip owns it in the shared Idea Bin.

**Vote unlock:** the new `IdeaBinItem` rows are instantly votable — `IdeaVote` rows are keyed only on `idea_id`, so the existing voting endpoints work as soon as the idea exists. No explicit "unlock" step needed.

**Transaction:** begin → insert all promoted rows into `idea_bin_items` (owned by trip, not user — Idea Bin is shared) → delete the source rows from `brainstorm_bin_items` → commit. Return the newly created `IdeaBinItem` list.

### 5. New endpoint for dashboard — `backend/app/api/endpoints/llm.py` (new file)

| Method | Path | Gating | Purpose |
|---|---|---|---|
| `POST` | `/api/llm/plan-trip` | authenticated | Calls `llm_client.plan_trip(prompt)`, returns preview (NOT persisted). |

The actual trip creation happens via the existing `POST /api/trips/` followed by `POST /api/trips/{id}/brainstorm/bulk` — composed on the client.

### 6. Router wiring

Register `brainstorm` and `llm` routers in `backend/app/api/router.py`.

### 7. Notifications

Emit `NotificationType.BRAINSTORM_PROMOTED` (new type) on promotion — fan-out to all trip members *except the promoter* so collaborators see "Alice added N ideas from her brainstorm to the Idea Bin." Add to `NotificationType` enum. No notifications are emitted for chat activity or brainstorm-item creation, since those are private to the member.

---

## Frontend Changes

### 1. Brainstorm section in Trip Planner — `frontend/app/trips/page.tsx`

- Extend `Mode` type: `'brainstorm' | 'plan' | 'concierge' | 'people'` (line 20).
- Insert a `sidebarBtn()` call **before** the Plan button in the nav container (line 364 area) with an appropriate icon (e.g., lightbulb / sparkles).
- Add a new `{mode === 'brainstorm' && <BrainstormSection tripId={id} />}` block before the Plan block (around line 415).
- Default mode should remain `plan` unless user explicitly navigates; don't change default.

### 2. New component — `frontend/components/trip/BrainstormSection.tsx` (new file)

Two-pane layout (flex, `grid-cols-[1fr_1fr]` on desktop, stacked on mobile):

**Left pane — `BrainstormChat.tsx` (sub-component):**
- Messages list (scrollable, user/assistant bubbles reusing existing Tailwind patterns).
- Text input + Send button.
- **"Create items from chat" button** inside the chat box area — calls `POST .../brainstorm/extract`. Visible only when there's ≥1 assistant message.
- On mount: `GET /brainstorm/messages` to hydrate history.

**Right pane — `BrainstormBin.tsx` (sub-component):**
- Fetches `GET /brainstorm/items` on mount + after extract/promote.
- Renders cards styled like `IdeaBin` cards (reuse Tailwind classes: `border border-slate-100 rounded-2xl shadow-sm`), but with a distinct accent color (e.g., amber/orange left stripe) so users can tell the bins apart.
- Fields shown: title, description, category badge, time_hint if present.
- **Selection state (local):** `selectionMode: boolean` + `selectedIds: Set<number>`. When `selectionMode=true`, clicking a card toggles border to highlighted state: `border-2 border-indigo-500 ring-2 ring-indigo-200` (vs default `border border-slate-100`). **No checkbox in corner.**
- **Bottom action bar (sticky):**
  - Default (not selecting): `[Select]` `[Add All to Idea Bin]`
  - Selecting: `[Cancel]` `[Send N selected to Idea Bin]` (disabled until ≥1 selected)
- On "Add All": `POST .../brainstorm/promote` with `{item_ids: null}` → list clears → trigger IdeaBin refresh (emit custom event or use Zustand/shared state).
- On "Send selected": `POST .../brainstorm/promote` with `{item_ids: [...]}` → selected items vanish → selection mode exits → toast confirmation.

### 3. Dashboard chatbox — `frontend/app/dashboard/page.tsx`

Insert a new component `<DashboardTripPlanner />` **above** `<TodayWidget />` (around line 305, before the existing widget block).

### 4. New component — `frontend/components/dashboard/DashboardTripPlanner.tsx` (new file)

- Single textarea (auto-grow) + **"Create Trip and Take Me There"** button on the right.
- Flow:
  1. Type prompt → click button.
  2. `POST /api/llm/plan-trip` with `{prompt}` → receives `{trip_name, start_date, duration_days, items}`.
  3. Show a **small preview panel** below the box: proposed trip name + date + item count. This prevents "clicked by accident → trip materialized" — one visible confirmation beat.
  4. Confirmation row: `[Create Trip]` / `[Dismiss]`.
  5. On Create Trip:
     - `POST /api/trips/` with `{name, start_date}` (duration_days → compute end_date client-side or let backend infer from trip_days).
     - On success: `POST /api/trips/{id}/brainstorm/bulk` with items.
     - Navigate `router.push('/trips?id=${newId}&mode=brainstorm')`.

### 5. Trip landing CTA — `frontend/app/trips/[id]/page.tsx`

Add a **"Go to Brainstorm"** button next to the existing "Open Planner" / "Live Concierge" / "People" CTAs (around line 571). Links to `/trips?id=${id}&mode=brainstorm`.

### 6. IdeaBin awareness

The existing `IdeaBin.tsx` component needs to refresh when promotion happens. Cheapest path: `BrainstormBin` dispatches a `CustomEvent('idea-bin:refresh')` on promote success; `IdeaBin.tsx` listens in a `useEffect` and re-fetches. Avoids introducing global state management for this single cross-component signal.

---

## Tests (new)

Backend — under `backend/tests/api/`:
- `test_brainstorm_api.py`:
  - chat append + persistence; extract hardcoded items (LLM disabled) populates all Google-Maps fields on `BrainstormBinItem`.
  - list items returns only caller's items; second user on same trip sees their own empty bin.
  - **per-user isolation**: Alice's messages/items are invisible to Bob; Bob deleting his own item leaves Alice's untouched; Bob cannot delete/promote an item owned by Alice (expect 404, not 403 — the item simply doesn't exist in Bob's scope).
  - promote-all and promote-subset (verify *move* semantics: Idea Bin gains rows, Brainstorm empties).
  - **full-field copy**: created Idea Bin row has every field copied (description, address, photo_url, rating, price_level, types, opening_hours, phone, website, time_hint, url_source) equal to source brainstorm row.
  - `added_by` on promoted Idea Bin row equals promoter's first name (not "AI") even when brainstorm item's original `added_by == "AI"`.
  - Any member role (view_only, view_with_vote, admin) can promote from their own brainstorm bin; non-members get 403.
  - Votes work immediately on a freshly promoted Idea Bin item.
  - Non-admin promoting does **not** bypass the admin-only Timeline gate (attempting to schedule the idea as an event still 403s for non-admins).
- `test_llm_plan_trip.py` — `POST /api/llm/plan-trip` returns hardcoded Thailand payload when `LLM_ENABLED=False`; items include full Google-Maps field set.

Backend — under `backend/tests/services/`:
- `test_llm_client.py` — with flag off, `chat`/`extract_items`/`plan_trip` return deterministic Bangkok fallback.

Target: +25–30 tests; full suite stays green (currently 439).

---

## Critical Files

**Modify:**
- `backend/app/models/all_models.py` — add `BrainstormBinItem` + `BrainstormMessage` models (with `user_id` FKs), add relationships on Trip, **extend `IdeaBinItem`** with the same Google-Maps fields (description, category, address, photo_url, rating, price_level, types, opening_hours, phone, website) for field-for-field promotion parity.
- `backend/app/schemas/trip.py` — add the new optional fields to `IdeaBinItemBase` / `IdeaBinItem` response schemas.
- `backend/app/core/config.py` — `LLM_ENABLED` flag.
- `backend/app/api/router.py` — register new routers.
- `backend/app/services/notification_service.py` + `NotificationType` enum — new `BRAINSTORM_PROMOTED` type.
- `frontend/app/trips/page.tsx` — add brainstorm mode to sidebar + render block.
- `frontend/app/trips/[id]/page.tsx` — add "Go to Brainstorm" CTA.
- `frontend/app/dashboard/page.tsx` — mount `<DashboardTripPlanner />` above TodayWidget.
- `frontend/components/trip/IdeaBin.tsx` — surface the new fields (description, photo_url, rating, etc.) in the existing card where space allows; at minimum render description and a photo thumbnail if present.

**Create:**
- `backend/app/schemas/brainstorm.py`
- `backend/app/services/llm_client.py`
- `backend/app/api/endpoints/brainstorm.py`
- `backend/app/api/endpoints/llm.py`
- `frontend/components/trip/BrainstormSection.tsx`
- `frontend/components/trip/BrainstormChat.tsx`
- `frontend/components/trip/BrainstormBin.tsx`
- `frontend/components/dashboard/DashboardTripPlanner.tsx`
- `backend/tests/api/test_brainstorm_api.py`
- `backend/tests/api/test_llm_plan_trip.py`
- `backend/tests/services/test_llm_client.py`

**Reuse:**
- `app/services/roles.py` — `require_trip_member`, `require_trip_admin` gating.
- `app/db/auto_migrate.py` — no migration script needed.
- `app/services/idea_bin.py` — pattern for batch-insert (mirror for brainstorm bulk).
- Frontend `authHeaders()` helper pattern from `IdeaBin.tsx` / `VoteControl.tsx`.
- `frontend/components/trip/IdeaBin.tsx` — card Tailwind classes for visual consistency (swap accent color).

---

## Verification

**Backend:**
1. `cd backend && pytest` — new tests pass; existing 439 stay green.
2. `pytest backend/tests/api/test_brainstorm_api.py -v` — specifically exercises chat persistence, extract, promote move-semantics, role gating.
3. Manual: hit `POST /api/llm/plan-trip` with any prompt — verify hardcoded Thailand/Bangkok payload with `LLM_ENABLED=False`.

**Frontend (manual, in-browser):**
1. Dashboard: type any prompt → click "Create Trip and Take Me There" → verify preview appears → click Create → lands on new trip's Brainstorm page with 6 Bangkok items in the creator's bin.
2. Brainstorm section visible in left sidebar before Plan; Plan still reachable; other modes unaffected.
3. Chat: send a message → assistant replies with Bangkok suggestions → click "Create items from chat" → 6 items appear in right pane, each showing description + rating + photo thumbnail (confirming full-field populate).
4. Click "Select" → card border highlights on click (no checkbox) → "Send N selected" promotes only those; rest remain in Brainstorm.
5. Click "Add All" → entire Brainstorm Bin empties; Idea Bin (visit Plan section) shows those items with all fields intact (photo, description, rating visible on Idea Bin cards too).
6. **Per-user isolation check:** log in as a second trip member (Bob). Bob's Brainstorm Bin is empty and chat history is empty, even though Alice's is populated on the same trip. Bob can start his own chat and create his own items without seeing Alice's.
7. **Cross-member promotion:** items Alice promoted appear in the **shared** Idea Bin for Bob; Idea Bin row's `added_by` shows "Alice" (promoter). Bob can vote on them immediately. Bob (if non-admin) still cannot schedule them onto the timeline — admin-only gate holds.
8. Confirm items cannot move back: no UI for Idea Bin → Brainstorm; Idea Bin only offers delete.
9. Trip landing page shows "Go to Brainstorm" CTA; clicking routes to `?mode=brainstorm`.
10. Collaborators (trip members other than the promoter) receive a notification on promotion; the promoter does not self-notify.

**LLM flag flip check:**
1. Set `LLM_ENABLED=true` in `.env` → restart → confirm fallback is bypassed (will fail without API key; OK, we're just checking the branch).
2. Revert to `false` → fallbacks resume.
