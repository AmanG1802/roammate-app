# [46] BACKEND_INTERNAL_URL — What It Is, the Proxy Bug, and the Fix

**Date:** 2026-06-09  
**Commits:** RM-061 (`0ba852f`)  
**Severity:** P0 — blocked Google (and Apple) sign-in on web for all users

---

## What BACKEND_INTERNAL_URL Is

The frontend has two env vars that both point at the Railway backend:

| Variable | Prefix | Where read | Who uses it |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | `NEXT_PUBLIC_` | Build time — baked into client JS bundle | Browser: all `fetch(${NEXT_PUBLIC_API_URL}/...)` calls in components, hooks, stores |
| `BACKEND_INTERNAL_URL` | (none) | Runtime — server-side only, never in client bundle | Vercel server: the auth proxy route handler + `next.config.js` rewrites |

`BACKEND_INTERNAL_URL` exists so the Vercel edge/lambda can reach Railway over the **private internal network** (e.g. `http://roammate-app.railway.internal/api`) instead of the public internet. Benefits: lower latency, no egress cost, no TLS overhead on the internal hop.

`NEXT_PUBLIC_API_URL` cannot serve this role because any `NEXT_PUBLIC_*` variable is compiled into the browser bundle and would expose the internal address (pointless — it's private anyway) or force the server-side proxy to use the public HTTPS URL unnecessarily.

### Where each is consumed in the codebase

```
next.config.js (rewrites)
  process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
  → rewrites /api/:path((?!auth/).*) to ${backend}/:path   (all non-auth API routes)

app/api/auth/[...path]/route.ts (cookie-forwarding auth proxy)
  process.env.BACKEND_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api'
  → proxies /api/auth/* to the backend, forwarding Set-Cookie for first-party cookies

Everything else (components, hooks, stores)
  process.env.NEXT_PUBLIC_API_URL
  → direct fetch from the browser with Bearer token header
```

---

## The Bug — ERR_CONTENT_DECODING_FAILED

### Symptom

Users saw **"Unexpected response from server. Please try again."** on the login page after clicking "Continue with Google" or "Sign in with Apple".

Chrome DevTools Network tab showed:

```
POST /api/auth/google   (failed)   net::ERR_CONTENT_DECODING_FAILED
```

### Root cause

The auth proxy in `app/api/auth/[...path]/route.ts` reads the backend response body and forwards it to the browser:

```typescript
// BUGGY code (before RM-061)
const res = await fetch(url, init);               // Vercel → Railway
const respHeaders = new Headers();
res.headers.forEach((value, key) => {
    respHeaders.append(key, value);               // ← forwarded ALL headers unchanged
});
const body = await res.arrayBuffer();             // ← Node.js fetch auto-decompresses here
return new NextResponse(body, { status: res.status, headers: respHeaders });
```

Node.js `fetch()` (undici) **automatically decompresses** gzip/br/deflate response bodies when `arrayBuffer()`, `json()`, or `text()` is called. So `body` contains the raw, already-decompressed bytes.

However, the proxy was blindly forwarding the original `Content-Encoding: gzip` header. The browser received:

- `Content-Encoding: gzip` → "this body is gzip-compressed, I must decompress it"
- Body: plain JSON bytes (already decompressed by Node.js)

The browser tried to decompress plaintext as gzip → `ERR_CONTENT_DECODING_FAILED` → `res.json()` threw a `SyntaxError` → surfaced as "Unexpected response from server."

The `Content-Length` header had the same problem: it reflected the compressed size, but the forwarded body was the larger decompressed size, causing potential truncation on some clients.

### Why it was latent for weeks

The proxy was introduced on **2026-05-16** (`cd94c59` — Auth refactor). At that point `BACKEND_INTERNAL_URL` pointed at Railway's internal HTTP URL (`http://roammate-app.railway.internal/api`). Internal Railway traffic over plain HTTP has **no compression middleware** — Railway's gzip layer sits on the TLS-terminating edge, not the internal hop. So `Content-Encoding: gzip` was never set, the bug never triggered, and Google/Apple auth worked fine.

### What changed to expose it

On **2026-06-09** (~15h before the incident was investigated), `BACKEND_INTERNAL_URL` was updated in Vercel to point at the **public HTTPS endpoint** (`https://api.roammate.xyz/api`). Requests now went through Railway's edge proxy, which adds `Content-Encoding: gzip` to JSON responses. The dormant proxy bug was immediately triggered for every auth response.

The same deploy included **RM-060**, which changed `api.ts` to replace the old `.catch(() => null)` silent suppression with an explicit `try/catch` that throws a user-friendly `ApiError`. This meant the failure was now visible as "Unexpected response from server" instead of a silent null-crash — which is what made the bug obvious to the user.

### Why only auth was affected (not other API calls)

The `next.config.js` rewrites are handled natively by Next.js, which manages Content-Encoding transparently — no double-decompression issue. Only the hand-written proxy in `route.ts` had the bug. Non-auth routes (trips, brainstorm, etc.) go through the Next.js rewrite, so they were unaffected.

---

## The Fix — RM-061

Strip `Content-Encoding` and `Content-Length` from the proxied response, since the body arriving at the browser is already decompressed:

```typescript
// app/api/auth/[...path]/route.ts — FIXED
res.headers.forEach((value, key) => {
    // Node.js fetch auto-decompresses the body, so forwarding Content-Encoding
    // would cause the browser to attempt a second decompression and fail with
    // ERR_CONTENT_DECODING_FAILED. Strip it (and Content-Length, whose value
    // changes after decompression inflates the size) so the browser reads the
    // raw bytes directly.
    const lower = key.toLowerCase();
    if (lower === 'content-encoding' || lower === 'content-length') return;
    // pass everything else including Set-Cookie
    respHeaders.append(key, value);
});
```

This fix is safe regardless of whether `BACKEND_INTERNAL_URL` points to:
- The internal Railway HTTP URL (no gzip → headers were never present anyway)
- The public HTTPS URL (gzip present → now correctly stripped)

---

## Current State of Env Vars

As of 2026-06-09, both vars point at the same public URL:

```
BACKEND_INTERNAL_URL = https://api.roammate.xyz/api   (Vercel, server-side only)
NEXT_PUBLIC_API_URL  = https://api.roammate.xyz/api   (Vercel, baked into browser bundle)
```

### Future: restoring the internal URL benefit

If you want to restore the original benefit (Vercel → Railway private network), set `BACKEND_INTERNAL_URL` back to the Railway internal address. The fix in RM-061 will work correctly because internal HTTP responses don't carry `Content-Encoding`.

```
BACKEND_INTERNAL_URL = http://roammate-app.railway.internal/api
```

Note: this only works from Vercel's serverless/edge runtime to Railway if they're in the same private network region. Verify connectivity before switching.

---

## Broader issue: most components bypass the proxy entirely

The majority of API calls in the frontend still use `NEXT_PUBLIC_API_URL` directly from the browser (Bearer-token style), bypassing the cookie-based proxy:

```typescript
// Seen in ~20 components/hooks
fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/members`, {
    headers: { Authorization: `Bearer ${token}` },
})
```

These work fine but don't benefit from httpOnly cookie auth. The auth proxy was introduced to make auth cookies first-party (needed for Safari ITP and cross-origin cookie restrictions) — only auth endpoints need to go through it. Non-auth routes either use the Next.js rewrite (transparent) or direct browser fetch (legacy Bearer).

---

## Security analysis: is the legacy Bearer pattern a problem?

### What's actually happening

`rm_access` (httpOnly cookie) and the `localStorage` Bearer token are **two copies of the same access token**. After Google/Apple/email sign-in:

1. The backend sets `rm_access` as an httpOnly cookie via the proxy (unreachable by JS)
2. `setToken(pair.access_token)` writes the same token to `localStorage`
3. The ~20 legacy components read it back from `localStorage` via `getToken()` and send it as `Authorization: Bearer`

`lib/auth.ts` documents this explicitly: *"Legacy localStorage token helpers — retained as a transition shim."*

### The actual risk: XSS

The only reason httpOnly cookies matter is **XSS protection**. If an attacker injects JavaScript into the page:

- `rm_access` cookie → **cannot be stolen** (httpOnly)
- `localStorage` token → **can be stolen** with `localStorage.getItem('token')`

The httpOnly cookie work is therefore partially neutralized — an XSS attacker bypasses it entirely by reading `localStorage`. You get the architecture of httpOnly without the full security benefit.

### What is NOT a risk

- **CSRF**: Backend uses `SameSite=lax` cookies. Lax blocks cross-site POST from third-party origins. Not an issue.
- **Cross-origin / Safari ITP**: The proxy makes auth cookies first-party on `roammate.xyz`. Solved regardless of the legacy Bearer calls.
- **Token exposure in transit**: HTTPS everywhere. Not an issue.

### How serious is this in practice?

**Low urgency for Roammate right now.** XSS is only exploitable if you have an XSS vulnerability to begin with. React escapes output by default, Next.js adds CSP headers, and the app doesn't render raw user HTML. The attack surface is narrow.

The real cost is **architectural debt** — two auth transports running in parallel, with `localStorage` as a hidden dependency that undermines the httpOnly investment.

### The clean fix (when you have time)

Finish the migration the auth refactor started. `lib/api.ts` already does cookie auth correctly with silent 401 refresh. The ~20 legacy fetch sites need to switch to it:

```typescript
// Legacy (~20 sites) — token in localStorage, XSS-stealable
fetch(`${process.env.NEXT_PUBLIC_API_URL}/trips/${tripId}/members`, {
    headers: { Authorization: `Bearer ${getToken()}` },
})

// Modern — cookie-based, relative URL through Next.js rewrite, no token in JS
import { api } from '@/lib/api';
api(`/api/trips/${tripId}/members`)
```

Once the last `getToken()` call is removed you can also:
- Remove `setToken` calls from the login/OAuth success handlers
- Stop writing `token` to `localStorage`
- Delete `lib/auth.ts` (or reduce it to just `clearSession`)

At that point `rm_access` becomes the sole session carrier and XSS protection is complete end-to-end.
