# Plan: Eliminate Unnecessary Periodic API Calls

## Context

Production logs show three endpoints being hammered: `/api/tutorial/status`, `/api/billing/status`, and `/api/notifications/unread-count`. The root causes are:

1. `TutorialProvider` and `EntitlementProvider` are mounted in the **root layout** (`app/layout.tsx`), so they fire API calls on every page — including unauthenticated pages (`/login`, `/signup`, `/pricing`). Both endpoints require auth and return 401 for anonymous users; those errors are silently swallowed, but the round-trips still happen.
2. Both providers attach `window.focus` and `visibilitychange` listeners with **no cooldown**, so every tab switch triggers fresh fetches for data that almost never changes.
3. No session-lifetime caching: even if data was fetched 5 seconds ago, navigating away and back fetches it again.

User decisions:
- Move providers behind an authenticated route group (not a client-side token check)
- Remove focus/visibilitychange re-fetch listeners entirely from tutorial and billing
- Cache for session lifetime: fetch once on mount; explicit actions (tutorial steps, subscription) already update state via their own API responses, so no extra invalidation needed
- Keep `NotificationBell` 30s polling as-is

---

## Changes

### 1. Create `(authenticated)` route group

**New file: `frontend/app/(authenticated)/layout.tsx`**

Move `EntitlementProvider`, `TutorialProvider`, `PaywallModal`, and `TutorialDriver` out of the root layout into this new authenticated layout. Route groups don't affect URL paths — `/dashboard`, `/trips`, `/profile` remain the same URLs.

```tsx
// frontend/app/(authenticated)/layout.tsx
import { EntitlementProvider } from '@/hooks/useEntitlement';
import { TutorialProvider } from '@/hooks/useTutorial';
import TutorialDriver from '@/components/tutorial/TutorialProvider';
import { PaywallModal } from '@/components/billing/PaywallModal';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <EntitlementProvider>
      <TutorialProvider>
        {children}
        <PaywallModal />
        <TutorialDriver />
      </TutorialProvider>
    </EntitlementProvider>
  );
}
```

### 2. Move protected routes into the group

Move these folders (no code changes inside them, just a directory rename):
- `frontend/app/dashboard/` → `frontend/app/(authenticated)/dashboard/`
- `frontend/app/trips/` → `frontend/app/(authenticated)/trips/`
- `frontend/app/profile/` → `frontend/app/(authenticated)/profile/`

Routes that stay in the root (public):
- `frontend/app/page.tsx` (landing)
- `frontend/app/pricing/page.tsx`
- `frontend/app/(auth)/` (login, signup, forgot, reset, verify)
- `frontend/app/admin/` (separate admin auth, unaffected)

### 3. Strip root layout

**Edit: `frontend/app/layout.tsx`**

Remove the four provider imports and their JSX. Root layout becomes just `ToastProvider` wrapping children.

```tsx
// After change — root layout only
import { ToastProvider } from '@/components/ui/Toast';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
```

### 4. Remove focus re-fetch from `useTutorial`

**Edit: `frontend/hooks/useTutorial.tsx`**

Delete the second `useEffect` block that adds `focus` and `visibilitychange` listeners. The `refresh()` on mount stays. All mutation functions (`start`, `advance`, `skip`, etc.) already call `post()` which updates state directly from the API response — no staleness possible after user actions.

```ts
// REMOVE this entire useEffect:
useEffect(() => {
  function onFocus() { void refresh(); }
  window.addEventListener('focus', onFocus);
  document.addEventListener('visibilitychange', onFocus);
  return () => {
    window.removeEventListener('focus', onFocus);
    document.removeEventListener('visibilitychange', onFocus);
  };
}, [refresh]);
```

### 5. Remove focus re-fetch from `useEntitlement`

**Edit: `frontend/hooks/useEntitlement.tsx`**

Inside the `useEffect` in `EntitlementProvider`, remove the focus listener lines. Keep the `refresh()` call on mount. The post-subscription polling loop in `resolvePaywall` (5× every 1.2s) stays — that's triggered only after a real purchase event.

```ts
// REMOVE these lines from the useEffect:
const onFocus = () => { refresh(); };
window.addEventListener('focus', onFocus);
return () => window.removeEventListener('focus', onFocus);

// useEffect becomes just:
useEffect(() => {
  refresh();
}, [refresh]);
```

---

## Files Modified

| File | Change |
|---|---|
| `frontend/app/layout.tsx` | Remove EntitlementProvider, TutorialProvider, PaywallModal, TutorialDriver |
| `frontend/app/(authenticated)/layout.tsx` | **New** — authenticated group layout with those providers |
| `frontend/app/dashboard/` | Move → `frontend/app/(authenticated)/dashboard/` |
| `frontend/app/trips/` | Move → `frontend/app/(authenticated)/trips/` |
| `frontend/app/profile/` | Move → `frontend/app/(authenticated)/profile/` |
| `frontend/hooks/useTutorial.tsx` | Remove focus/visibilitychange useEffect |
| `frontend/hooks/useEntitlement.tsx` | Remove focus listener from mount useEffect |

---

## Notes

- `pricing/page.tsx` uses `useEntitlement` but already has a provider-less fallback that returns `FREE_DEFAULT` — it will continue to work correctly outside the authenticated group.
- `(auth)/layout.tsx` (login/signup pages) is currently a pass-through — no changes needed.
- iOS is unaffected — these are purely web frontend changes.
- No backend changes required.

---

## Verification

1. **Unauthenticated pages**: Visit `/login`, `/signup`, `/pricing` — check Railway logs to confirm zero `tutorial/status` and `billing/status` calls originate from those page loads.
2. **Tab switch**: Open `/dashboard`, switch tabs repeatedly — confirm no new `tutorial/status` or `billing/status` entries appear in logs.
3. **Auth flow**: Log in via Google → confirm `tutorial/status` and `billing/status` are fetched exactly once after redirect to `/dashboard`.
4. **Tutorial actions**: Complete/skip a tutorial step — confirm state updates correctly (mutation already returns updated state from backend).
5. **Subscription flow**: Trigger the paywall and complete a purchase — confirm billing status is re-fetched correctly via the existing post-purchase polling loop.
6. **Routing**: Confirm `/dashboard`, `/trips`, `/profile` URLs are unchanged after the route group move.
