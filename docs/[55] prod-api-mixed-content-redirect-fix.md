# [55] Production API mixed-content / redirect fix

**Status:** Implemented
**Branch:** aman/update-ripple-engine-and-concierge
**Date:** 2026-06-14

## Symptom

After moving production to the same-origin proxy model (`BACKEND_INTERNAL_URL` →
Railway), login worked but `/api/trips/` (and other collection endpoints) failed
in the browser with `net::ERR_... blocked:mixed-content`. The dashboard showed
"Couldn't load your trips."

## Root cause

Two stacked backend bugs, proven by curl against both the Vercel proxy and the
backend directly:

```
$ curl -D - https://api.roammate.xyz/api/trips/
HTTP/2 307
location: http://api.roammate.xyz/api/trips     # http:// + slash dropped
```

### Bug 1 — backend emits `http://` absolute redirects (the actual blocker)

Railway terminates TLS at its edge and forwards to the container over plain HTTP
with `X-Forwarded-Proto: https`. Uvicorn was started as:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

By default uvicorn only trusts forwarded headers from `127.0.0.1`. Railway's
proxy is not `127.0.0.1`, so uvicorn ignores `X-Forwarded-Proto`, believes the
request is `http`, and Starlette builds absolute redirect `Location` headers with
scheme `http://`. The browser receives a 307 → `http://...` from an `https` page
and blocks it as mixed content.

This affects **every** absolute URL the backend generates (redirects, OAuth
callbacks, pagination links), not just trips.

### Bug 2 — trailing-slash mismatch causes the redirect to exist at all

- Frontend calls `/api/trips/` (trailing slash); `next.config.js` deliberately
  preserved the slash.
- The live spec-first router (`app/main.py:77`, built from `openapi.yaml`)
  defines the path as `/api/trips` — **no trailing slash**. No spec path uses a
  trailing slash.
- FastAPI's default `redirect_slashes=True` therefore 307s `/api/trips/` →
  `/api/trips`.

The `next.config.js` comment assumed the backend route was `/api/trips/` with a
slash — that assumption was wrong. (`app/api/router.py`, which uses
`prefix="/trips" + "/"`, is dead code: not mounted anywhere.)

Why it surfaced now: the same-origin proxy is the first time the browser actually
traverses this redirect. Login worked because the auth Route Handler uses
`redirect: 'manual'` and reads env at runtime.

## Fix

### Part 1 — backend trusts the proxy (fixes mixed content at the root)

`backend/Dockerfile` CMD:

```
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
```

Canonical config for an ASGI app behind a TLS-terminating reverse proxy. `*` is
safe because Railway is the single trusted hop in front of the container. After
this, absolute redirects use `https://`.

### Part 2 — eliminate the redirect (keeps the same-origin proxy intact)

Even with Part 1, `/api/trips/` still 307s to the absolute backend origin
`https://api.roammate.xyz/api/trips`, bouncing the browser off the same-origin
proxy and onto the backend cross-origin (relying on CORS + SameSite). The proxy
design wants the browser to never see the backend host.

Source of truth is the spec (no slash). Drop trailing slashes from frontend
`/api/...` calls so there is no redirect. Affected call sites:

- `app/(authenticated)/dashboard/page.tsx` — `/api/trips/` ×3
- `components/dashboard/DashboardTripPlanner.tsx` — `/api/trips/`
- `components/groups/GroupsPanel.tsx` — `/api/trips/`, `/api/groups/` ×2
- `components/layout/NotificationBell.tsx` — `/api/notifications/?limit=30`
- `lib/store.ts` — `/api/events/?trip_id=...`, `/api/events/`

Update the now-incorrect `next.config.js` comment.

## Follow-up (not in this change)

Two proxy mechanisms exist: build-time `next.config.js` rewrites for non-auth +
a runtime Route Handler for auth. The rewrite bakes the backend URL at build time
and falls back to `http://localhost:8000` when env is unset — how an empty env
silently shipped a broken target. Consolidating to a single runtime proxy would
remove that failure class. Tracked separately.

## Verification

- Frontend: `tsc --noEmit` + `vitest run` green.
- Backend: `pytest` green; uvicorn accepts `--proxy-headers --forwarded-allow-ips`.
- Post-deploy: `curl -D - https://api.roammate.xyz/api/trips` returns a direct
  2xx/4xx (no 307), and any redirect `Location` uses `https://`.
