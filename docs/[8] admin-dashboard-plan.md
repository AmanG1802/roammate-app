# Plan: Roammate Admin Dashboard (`/admin`)

## Context

No admin panel exists in the codebase. Token and Google Maps usage is currently **log-only** (structured stdout via `roammate.tokens` and `roammate.google_maps` loggers) with no DB persistence. This plan builds:

1. **DB persistence** for both trackers (new Postgres tables)
2. A **separate admin API** (`/api/admin/*`) with its own hardcoded-credential auth (no dependency on user JWT)
3. A **Next.js `/admin` route** with a login gate and a 3-section metrics dashboard

The page is internal-only and never linked from the main app UI.

---

## Design System (from ui-ux-pro-max)

- **Style:** Data-Dense Dashboard — minimal padding, KPI cards, filterable tables
- **Colors:** Primary `#1E40AF` (indigo-800), Secondary `#3B82F6` (blue-500), Background `#F8FAFC` (slate-50), Sidebar `#0F172A` (slate-900), Sidebar text `#94A3B8` (slate-400), Active item `#1E40AF` bg + white text
- **Typography:** Existing Tailwind (no new fonts) — consistent with codebase using `font-sans`
- **Icons:** `lucide-react` (already installed) — no emojis
- **Components:** Raw Tailwind (no shadcn/ui installed; project uses Tailwind directly)

### ASCII Layout Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ ■ Roammate Admin                                            │
├────────────────┬────────────────────────────────────────────┤
│                │  Section Title              [Filter Bar]   │
│  Users         │                                            │
│  AI Token Usage│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  Maps API      │  │ KPI Card │ │ KPI Card │ │ KPI Card │   │
│                │  └──────────┘ └──────────┘ └──────────┘   │
│                │                                            │
│                │  ┌─────────────────────────────────────┐   │
│                │  │ [Search...]  [Model ▼] [Month ▼]    │   │
│                │  ├──────┬──────┬──────┬──────┬─────────┤   │
│                │  │ Name │Email │Model │Tokens│ Cost    │   │
│                │  ├──────┼──────┼──────┼──────┼─────────┤   │
│                │  │  ... │  ... │  ... │  ... │  ...    │   │
│                │  └─────────────────────────────────────┘   │
│                │                                            │
│  ─────────     │                                            │
│  Logout        │                                            │
└────────────────┴────────────────────────────────────────────┘
```

### Login Page Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                  ■ Roammate Admin                           │
│                                                             │
│            ┌──────────────────────────┐                    │
│            │ Username                 │                    │
│            │ [________________________]                    │
│            │                          │                    │
│            │ Password                 │                    │
│            │ [________________________]                    │
│            │                          │                    │
│            │  [    Sign In    ]        │                    │
│            └──────────────────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Backend — Database Models

**File to modify:** `backend/app/models/all_models.py`

Add two new SQLAlchemy models:

### `TokenUsage`
```python
class TokenUsage(Base):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    trip_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)
    op: Mapped[str]                    # chat | extract | plan_trip
    provider: Mapped[str]              # openai | claude | gemini
    model: Mapped[str]                 # specific model name
    tokens_in: Mapped[int]
    tokens_out: Mapped[int]
    tokens_total: Mapped[int]
    source: Mapped[Optional[str]]      # brainstorm | concierge | plan_trip
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
```

### `GoogleMapsApiUsage`
```python
class GoogleMapsApiUsage(Base):
    __tablename__ = "google_maps_api_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    trip_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)
    op: Mapped[str]                    # find_place | place_details | photo_url | directions | enrich_batch
    status: Mapped[str]                # ok | error | cache_hit | cache_negative | circuit_open | zero_results
    latency_ms: Mapped[Optional[int]]
    attempts: Mapped[Optional[int]]
    cache_state: Mapped[Optional[str]] # hit | miss | negative
    breaker_state: Mapped[Optional[str]]
    http_status: Mapped[Optional[int]]
    error_class: Mapped[Optional[str]]
    batch_size: Mapped[Optional[int]]
    enriched_count: Mapped[Optional[int]]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
```

The project uses `create_all` in the lifespan startup — these tables auto-create on next server start.

---

## Phase 2: Backend — Update Trackers to Persist to DB

### Cost Constants

Add a new file `backend/app/services/admin_costs.py`:
```python
TOKEN_PRICING = {  # USD per 1M tokens
    ("openai", "gpt-4o-mini"):              {"input": 0.15,  "output": 0.60},
    ("claude", "claude-sonnet-4-20250514"): {"input": 3.00,  "output": 15.00},
    ("gemini", "gemini-2.0-flash"):         {"input": 0.075, "output": 0.30},
}

MAPS_PRICING = {  # USD per 1K non-cache calls
    "find_place":    17.00,
    "place_details": 17.00,
    "photo_url":      7.00,
    "directions":    10.00,
    "enrich_batch":   0.00,  # composed of find_place + place_details — don't double-count
}
```

### Token Tracker — `backend/app/services/llm/token_tracker.py`

Add an async `_persist_token_usage(record: dict)` function that:
1. Creates a new `AsyncSession` using `async_session_factory` from `backend/app/db/session.py`
2. Computes `cost_usd` from `TOKEN_PRICING`
3. Inserts a `TokenUsage` row and commits

In `track()`, add: `asyncio.create_task(_persist_token_usage(record))` — fire-and-forget, non-blocking, doesn't break existing logging.

### Maps Tracker — `backend/app/services/google_maps/tracker.py`

Same pattern: add `_persist_maps_usage(record: dict)`. The `user_id` must be threaded in from callers. Update `track_call()` to accept an optional `user_id: Optional[int] = None` parameter.

**Propagation**: The maps service base (`base.py`) calls `track_call`. Add `user_id` to `enrich_batch`, `find_place`, `directions` etc. signatures. API endpoints that call the maps service have the current user — pass `current_user.id` down.

---

## Phase 3: Backend — Admin Config & Auth

### Config — `backend/app/core/config.py`

Add:
```python
ADMIN_USERNAME: str = "admin"
ADMIN_PASSWORD: str = "password@123"
ADMIN_TOKEN_EXPIRE_HOURS: int = 4
```

### Admin Auth Dependency — `backend/app/api/deps.py`

Add:
```python
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

def get_admin(token: str = Depends(admin_oauth2_scheme)) -> bool:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if not payload.get("admin"):
        raise HTTPException(status_code=403)
    return True
```

---

## Phase 4: Backend — Admin Endpoints

**New file:** `backend/app/api/endpoints/admin.py`

```
POST /api/admin/login          → validates hardcoded creds, returns JWT {"admin": true, exp: +4h}

GET  /api/admin/users          → all users: id, name, email, created_at + total count

GET  /api/admin/token-usage/summary
     ?model=&provider=&month=YYYY-MM&day=YYYY-MM-DD
     → {total_tokens, total_cost_usd, by_provider: {...}, by_model: {...}, by_source: {...}}

GET  /api/admin/token-usage/users
     ?model=&provider=&month=&day=&search=  (name or email substring)
     → [{user_id, name, email, tokens_total, tokens_in, tokens_out, cost_usd, top_model, top_source}]

GET  /api/admin/maps-usage/summary
     ?ops[]=find_place&ops[]=directions&month=&day=
     → {total_calls, cache_hits, cache_hit_rate_pct, error_count, error_rate_pct, total_cost_usd, by_op: {...}}

GET  /api/admin/maps-usage/users
     ?ops[]=&month=&day=&search=
     → [{user_id, name, email, calls_by_op: {find_place: N, ...}, total_cost_usd}]
```

All GET endpoints require `Depends(get_admin)`. Login endpoint is public.

**Register in** `backend/app/api/router.py`:
```python
from app.api.endpoints import admin
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
```

---

## Phase 5: Frontend — Admin Route

### File Structure

```
frontend/app/admin/
  layout.tsx           ← bare layout, no main nav header
  page.tsx             ← login page (redirects to /admin/dashboard if session exists)
  dashboard/
    page.tsx           ← full dashboard
frontend/hooks/useAdminAuth.tsx  ← admin session hook
```

### `useAdminAuth.tsx`

- Stores admin token in `sessionStorage` (key: `admin_token`) — clears on browser close
- Validates token by calling `GET /api/admin/users` on mount
- Exposes `{ adminToken, login(user, pass), logout, isLoading }`

### `app/admin/page.tsx` — Login Page

Centered card on dark background (`bg-slate-900`). Fields: Username, Password (with show/hide toggle). On submit: `POST /api/admin/login`, store token, redirect to `/admin/dashboard`. Error shown below form.

### `app/admin/dashboard/page.tsx` — Dashboard

**Layout:** Flex row — dark sidebar (w-56, `bg-slate-900`) + content area (`bg-slate-50 flex-1`).

**Sidebar items** (with Lucide icons):
- `Users` (Users icon)
- `AI Token Usage` (Zap icon)
- `Google Maps API` (Map icon)
- separator
- `Logout` (LogOut icon) — at bottom

Active item: `bg-slate-800 text-white`, inactive: `text-slate-400 hover:text-white hover:bg-slate-800`.

**Shared components** (inline in dashboard, no new component files):
- `KpiCard` — white card, label (small gray), value (large bold), optional subtitle
- `FilterBar` — flex row of `<select>` dropdowns + search `<input>`
- `DataTable` — striped `<table>` with sortable headers, skeleton loading state

---

### Section: Users

**KPI cards:** Total Users | New This Month (last 30 days)

**Table columns:** Name · Email · Joined (date formatted as "Jan 15, 2025")

**Controls:** Search input filtering by name or email (client-side filter on loaded data)

**API call:** `GET /api/admin/users`

---

### Section: AI Token Usage

**KPI cards:** Total Tokens · Total Cost (USD) · Avg Tokens/Request · Top Model

**Filter bar:**
- Provider dropdown: All | OpenAI | Claude | Gemini
- Model dropdown: populated from provider selection
- Month picker: YYYY-MM select (last 12 months)
- Day picker: calendar date input (optional)

**Table columns:** User · Email · Tokens In · Tokens Out · Total Tokens · Est. Cost · Top Model · Top Source

**Search:** filter table by name or email

**API calls:** `GET /api/admin/token-usage/summary` + `GET /api/admin/token-usage/users`

---

### Section: Google Maps API Usage

**KPI cards:** Total API Calls · Cache Hit Rate · Error Rate · Total Cost (USD)

**Filter bar:**
- API type multi-select: checkboxes in a dropdown popover for `find_place`, `place_details`, `photo_url`, `directions`, `enrich_batch` — all selected by default
- Month picker
- Day picker

**Table columns:** User · Email · [one column per selected API type showing call count] · Total Calls · Est. Cost

**Search:** filter table by name or email

**API calls:** `GET /api/admin/maps-usage/summary` + `GET /api/admin/maps-usage/users`

---

## Critical Files to Modify / Create

| File | Action |
|------|--------|
| `backend/app/models/all_models.py` | Add `TokenUsage`, `GoogleMapsApiUsage` models |
| `backend/app/services/admin_costs.py` | Create — pricing constants |
| `backend/app/services/llm/token_tracker.py` | Add `_persist_token_usage()`, fire via `asyncio.create_task` |
| `backend/app/services/google_maps/tracker.py` | Add `_persist_maps_usage()`, add `user_id` param to `track_call` |
| `backend/app/services/google_maps/base.py` | Thread `user_id` through to `track_call` |
| `backend/app/api/deps.py` | Add `get_admin` dependency |
| `backend/app/core/config.py` | Add `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_TOKEN_EXPIRE_HOURS` |
| `backend/app/api/endpoints/admin.py` | Create — all admin endpoints |
| `backend/app/api/router.py` | Register admin router |
| `frontend/hooks/useAdminAuth.tsx` | Create — admin session management |
| `frontend/app/admin/layout.tsx` | Create — bare layout |
| `frontend/app/admin/page.tsx` | Create — login page |
| `frontend/app/admin/dashboard/page.tsx` | Create — full dashboard |

---

## Security Notes

- Admin token uses same `SECRET_KEY` as user tokens but carries `{"admin": true}` claim — `get_admin` rejects user JWTs
- `sessionStorage` (not `localStorage`) — session ends when browser tab closes
- No link to `/admin` anywhere in the main app UI
- CORS is already `*` for dev — production should restrict `/api/admin/*` to known IPs (out of scope for now)
- Password is hardcoded in config; move to env var when needed

---

## Verification

1. Start backend → confirm `token_usage` and `google_maps_api_usage` tables are created
2. `POST /api/admin/login` with correct creds → 200 + token; wrong creds → 401
3. `GET /api/admin/users` without token → 401; with admin token → user list
4. Trigger a brainstorm or plan-trip flow → check `SELECT * FROM token_usage` populated with cost
5. Trigger a place search (un-mock) → check `SELECT * FROM google_maps_api_usage` populated
6. Navigate to `http://localhost:3000/admin` → login form appears
7. Login → redirected to `/admin/dashboard`, all 3 sidebar sections work with filter changes
8. Close browser tab → reopen `/admin/dashboard` → redirected back to login (sessionStorage cleared)
