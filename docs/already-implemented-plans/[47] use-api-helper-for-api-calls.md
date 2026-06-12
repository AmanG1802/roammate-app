# Migrate Legacy Direct Fetch Calls to `api()` Helper

## Context

~20 frontend files bypass the `api()` helper and call `process.env.NEXT_PUBLIC_API_URL` directly
from the browser using `Authorization: Bearer ${getToken()}`. This is the architectural debt
documented in docs/[46]. It means:

- No automatic 401 refresh/retry (components silently fail on token expiry)
- Token sits in `localStorage`, stealable by XSS (undermines the httpOnly `rm_access` cookie)
- Mixed-content risk if `NEXT_PUBLIC_API_URL` ever becomes HTTP (which triggered today's bug)
- Duplicate auth transport running in parallel with the cookie-based system

The fix: migrate every legacy call to `api('/api/...')` (cookie-based, proxied, auto-refresh).
Admin panel (`app/admin/`, `hooks/useAdminAuth.tsx`) is excluded — it uses a separate,
intentionally different auth system (sessionStorage, separate credentials).

---

## What `api()` Already Does (no changes needed)

`frontend/lib/api.ts`:
- All calls use relative `/api/...` paths (proxied server-side via `next.config.js` rewrites)
- `credentials: 'include'` — sends `rm_access` httpOnly cookie automatically
- On 401, calls `/api/auth/refresh` once (deduped), then retries original request
- Auto-parses JSON, throws typed `ApiError(status, message, data)` on non-2xx
- `json` option sets body + Content-Type in one step

---

## Migration Pattern

Every legacy call follows the same mechanical transformation:

```ts
// BEFORE
const token = getToken();
const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/members`, {
  headers: { Authorization: `Bearer ${token}` },
});
if (!res.ok) throw new Error('Failed');
const data = await res.json();

// AFTER
import { api } from '@/lib/api';
const data = await api(`/api/trips/${tripId}/members`);
```

- Drop the Bearer header entirely (cookie auth is automatic)
- Drop `res.ok` check + manual `res.json()` (api() does both)
- Wrap in try/catch `ApiError` for error handling (same as already done in dashboard/page.tsx)
- `json` option replaces manual `JSON.stringify` + Content-Type header

---

## Files to Migrate (in order)

### Batch 1 — Simple components (1–2 calls each)
| File | Calls | Notes |
|---|---|---|
| `components/dashboard/TodayWidget.tsx` | 1 | GET /dashboard/today |
| `components/trip/ConciergeActionBar.tsx` | 1 | POST /events/ripple/{id} |
| `contexts/PersonaCatalogContext.tsx` | 1 | GET /users/personas/catalog (no auth needed, keep as-is if public) |
| `components/billing/CouponInput.tsx` | 1 | POST /billing/coupons/validate |
| `app/profile/subscription/page.tsx` | 1 | POST /billing/cancel |

### Batch 2 — Medium components (3–5 calls each)
| File | Calls | Notes |
|---|---|---|
| `components/trip/BrainstormChat.tsx` | 3 | GET messages, POST chat, POST extract |
| `components/trip/IdeaBin.tsx` | 4 | GET/POST/DELETE/PATCH ideas |
| `components/trip/BrainstormBin.tsx` | 4 | GET/POST/DELETE brainstorm items |
| `components/dashboard/DashboardTripPlanner.tsx` | 4 | POST plan-trip, POST trips/, POST bulk, POST seed |
| `hooks/useProfile.ts` | 4 | GET/PUT/DELETE /users/me + personas |
| `components/map/GoogleMap.tsx` | unknown | Fetch routes/enrichment |
| `components/trip/VoteControl.tsx` | unknown | Vote endpoints |
| `components/trip/ConciergeChatDrawer.tsx` | unknown | Concierge chat |

### Batch 3 — Heavy files (6+ calls each)
| File | Calls | Notes |
|---|---|---|
| `components/layout/NotificationBell.tsx` | ~4 | GET unread-count, notifications list, mark-read |
| `components/groups/GroupsPanel.tsx` | ~14 | Full CRUD for groups, members, invitations, trips |
| `app/trips/page.tsx` | 6 | Member management, trip refresh, ideas |
| `lib/store.ts` | 13+ | Zustand actions: events, trip days, ideas, enrichment |

---

## Cleanup After All Migrations

Once every legacy call is migrated and `getToken()` has no remaining callers outside admin:

1. **`lib/auth.ts`**: Remove `getToken()`, `setToken()`. Keep `clearSession()` (still needed for logout to clear localStorage `user` key). The `localStorage.removeItem('token')` line in `clearSession` can also be removed at this point.

2. **Auth success handlers** (login, OAuth callbacks in `app/login/`, `components/auth/OAuthButtons.tsx`):
   Remove `setToken(pair.access_token)` calls — the cookie is the sole session carrier.

3. **`localStorage` key `'token'`**: No longer written after step 2, no longer read after step 1.
   The `'user'` key in localStorage (cached user JSON) can stay as-is (used by `useAuth` as offline fallback).

4. **Imports**: Remove `getToken`/`authHeaders`/`auth()` helper imports from each migrated file.

---

## Verification

After each batch, test the affected features manually in the browser:

1. **Network tab**: Migrated endpoints should show as `/api/...` (same-origin), not `https://api.roammate.xyz/...` (cross-origin)
2. **Auth**: Confirm requests carry no `Authorization` header — auth flows via cookie only
3. **401 refresh**: Let token expire (or clear `rm_access` cookie temporarily) — `api()` should auto-refresh silently
4. **Smoke test per batch**: Today widget, concierge, brainstorm chat, idea bin, groups panel, trip page member management

Final grep to confirm no legacy calls remain (excluding admin and node_modules):
```bash
grep -r "NEXT_PUBLIC_API_URL" frontend --include="*.ts" --include="*.tsx" \
  | grep -v "node_modules" | grep -v "app/admin" | grep -v "useAdminAuth" \
  | grep -v "next.config" | grep -v "route.ts"
# Should output nothing
```
