# Auth Refactor: Google + Apple + Email-with-Verification (Web + iOS)

## Context

Today Roammate has a single auth path: email + bcrypt + 8-day JWT, no email verification, token in `localStorage` on web and Keychain on iOS. There is no email service, no OAuth, and no `email_verified` column. The User model is the foreign-key root for all subscription and entitlement logic, so the refactor must preserve `users.id` and the existing row for any current account.

Goals:
- Add **Google Sign-In**, **Sign in with Apple**, and **email + password** with mandatory **email verification** on both web and iOS.
- Move web token to HTTP-only cookies and add Next.js middleware for server-side route protection.
- Replace the 8-day JWT with short-lived access + long-lived refresh tokens (rotation).
- Add password reset, linked-identity management, and email-change flows.
- Backfill behavior: existing users keep their row; on first login after rollout they are required to verify their email (one-time prompt).
- Preserve the current visual language: indigo `#4F46E5` brand, Inter on web / SF Rounded on iOS, the existing button spring + view-transition crossfade.

**Note:** Apple App Store guideline 4.8 requires Sign in with Apple if Google Sign-In is offered on iOS — included by default.

---

## Decisions (confirmed)

| Area | Decision |
|---|---|
| Email provider | **Resend** (`@resend/node` + React Email templates) |
| Web token storage | **HTTP-only cookie** + Next.js `middleware.ts` (Secure, SameSite=Lax, set by backend) |
| Account linking | **Auto-link if email is verified.** If existing row is unverified → block OAuth login, force them to verify or sign in with password first. |
| In scope v1 | Password reset, refresh tokens, linked-identities settings UI, force re-verify for existing users on next login |

---

## Architecture overview

```
                 ┌─────────────────────┐
   Web (Next.js) │ middleware.ts       │── reads `rm_access` cookie, refreshes via `rm_refresh`
                 │ (auth)/* pages      │── login, signup, verify-email, reset, callback
                 │ /api/auth/* proxy   │── forwards to backend, sets HttpOnly cookies
                 └──────────┬──────────┘
                            │
   iOS (SwiftUI)            │            Backend (FastAPI)
   AuthManager + Keychain   │            ┌─────────────────────────────┐
   GoogleSignIn-iOS  ───────┼──────────▶ │ /auth/google   POST id_token │
   ASAuthorization*  ───────┼──────────▶ │ /auth/apple    POST id_token │
   email/password    ───────┼──────────▶ │ /auth/signup   (sends email) │
                            │            │ /auth/verify   (token in URL)│
                            │            │ /auth/login                  │
                            │            │ /auth/refresh                │
                            │            │ /auth/logout                 │
                            │            │ /auth/password/forgot|reset  │
                            │            │ /auth/me/identities          │
                            │            └──────────────┬──────────────┘
                            │                           │
                            │                           ▼
                            │                  Postgres: users, user_identities,
                            │                  email_verifications, password_resets,
                            │                  refresh_tokens
                            ▼
                  Resend (transactional email)
```

---

## Backend (FastAPI)

### New schema — `backend/migrations/004_auth.sql`

```sql
ALTER TABLE users
  ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN email_verified_at TIMESTAMPTZ NULL,
  ADD COLUMN auth_version INT NOT NULL DEFAULT 1;  -- bump to invalidate refresh tokens

CREATE TABLE user_identities (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider        TEXT NOT NULL,           -- 'google' | 'apple'
  subject         TEXT NOT NULL,           -- provider's stable user id (sub)
  email_at_link   TEXT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, subject)
);
CREATE INDEX ON user_identities(user_id);

CREATE TABLE email_verifications (
  token_hash      TEXT PRIMARY KEY,        -- sha256 of token; raw token only emailed
  user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email           TEXT NOT NULL,           -- email being verified (supports email change)
  purpose         TEXT NOT NULL,           -- 'signup' | 'change_email'
  expires_at      TIMESTAMPTZ NOT NULL,
  consumed_at     TIMESTAMPTZ NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE password_resets (
  token_hash      TEXT PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at      TIMESTAMPTZ NOT NULL,
  consumed_at     TIMESTAMPTZ NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash      TEXT NOT NULL UNIQUE,
  device_label    TEXT NULL,               -- "iPhone 15 / Safari macOS"
  parent_id       BIGINT NULL REFERENCES refresh_tokens(id), -- rotation chain
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ NULL,
  last_used_at    TIMESTAMPTZ NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON refresh_tokens(user_id);

-- Backfill: existing users must verify on next login.
-- email_verified stays FALSE for everyone; legacy login path will redirect them
-- through a one-time verification flow (see Migration & Rollout below).
```

### Token strategy
- **Access token**: JWT HS256, `exp = 15 min`, claims `{sub, ver, iat, exp}` (`ver` = `users.auth_version`; bumping it instantly invalidates all sessions for that user — used on password change and "log out everywhere").
- **Refresh token**: opaque random 32-byte URL-safe string, **stored hashed (sha256)** in `refresh_tokens`, `exp = 30 days`, **rotated on every use**. Reuse of a consumed refresh token revokes the entire chain (token-theft detection).
- **Logout**: revoke current refresh token + clear cookies (web) / Keychain (iOS).

### New service modules
- `backend/app/services/auth/tokens.py` — issue/verify access tokens; mint, hash, rotate refresh tokens
- `backend/app/services/auth/oauth_google.py` — verify Google ID token via `google-auth` (`id_token.verify_oauth2_token`, audience = web client ID **or** iOS client ID)
- `backend/app/services/auth/oauth_apple.py` — verify Apple ID token: fetch JWKS from `https://appleid.apple.com/auth/keys`, validate `iss=https://appleid.apple.com`, `aud=<bundle id or web service id>`, `nonce`
- `backend/app/services/auth/email.py` — Resend client wrapper, retry once
- `backend/app/services/auth/templates/` — React Email-compatible HTML templates: `verify_email.html`, `reset_password.html`, `email_changed.html`
- `backend/app/services/auth/linking.py` — find-or-create + auto-link logic (verified-email rule)

### New endpoints — `backend/app/api/endpoints/auth.py` (replaces password-only paths in `users.py`)

```
POST /auth/signup              {email, password, name}     → 200 + sends verify email
POST /auth/verify              {token}                     → 200 {access_token} + sets cookies
POST /auth/verify/resend       {email}                     → 204
POST /auth/login               {email, password}           → 200 (requires email_verified) or 409 unverified
POST /auth/google              {id_token, platform}        → 200 + cookies
POST /auth/apple               {id_token, nonce, platform} → 200 + cookies
POST /auth/refresh             (cookie or body)            → 200 (new pair)
POST /auth/logout              → 204 (revokes refresh, clears cookies)
POST /auth/password/forgot     {email}                     → 204 (always 204 to avoid enumeration)
POST /auth/password/reset      {token, new_password}       → 200
GET  /auth/me/identities       → list of linked providers
DELETE /auth/me/identities/{provider}   → 204 (block if it's the only auth method)
POST /auth/me/email/change     {new_email, password}       → 204 (sends verify to new addr)
```

`backend/app/api/deps.py:get_current_user` is updated to require `email_verified=True`; a separate `get_current_user_unverified` is used by `/auth/verify/resend` only.

Old `/users/register` and `/users/login` are **deleted** (no callers besides the two clients we're refactoring).

### Config additions — `backend/app/core/config.py`
```
RESEND_API_KEY
EMAIL_FROM                 # "Roammate <auth@roammate.app>"
PUBLIC_WEB_URL             # for verify/reset links
GOOGLE_OAUTH_CLIENT_ID_WEB
GOOGLE_OAUTH_CLIENT_ID_IOS
APPLE_SIGNIN_BUNDLE_ID     # com.roammate.app
APPLE_SIGNIN_SERVICE_ID    # for web (Sign in with Apple JS)
APPLE_SIGNIN_TEAM_ID
ACCESS_TOKEN_TTL_MIN=15
REFRESH_TOKEN_TTL_DAYS=30
COOKIE_DOMAIN              # .roammate.app in prod, blank locally
```

`.env.example` updated to match.

---

## Web (Next.js App Router)

### Routes (replace single `(auth)/login/page.tsx`)
```
app/(auth)/
  layout.tsx            ← shared centered card layout, brand mark, transitions
  login/page.tsx        ← email + Google + Apple + "Forgot password?"
  signup/page.tsx       ← email + Google + Apple
  verify/page.tsx       ← consumes ?token=, shows success → /dashboard
  verify/check/page.tsx ← "We sent you an email" idle state w/ resend button
  forgot/page.tsx       ← email entry
  reset/page.tsx        ← consumes ?token=, new-password form
  callback/google/page.tsx   ← (only if we use redirect flow; GIS one-tap doesn't need this)
```

### Token cookies + middleware
- Backend sets two cookies on successful auth: `rm_access` (15m, HttpOnly, Secure, SameSite=Lax) and `rm_refresh` (30d, HttpOnly, Secure, SameSite=Lax, Path=/api/auth/refresh).
- New `frontend/middleware.ts`:
  - If `rm_access` valid → allow.
  - Else if `rm_refresh` present → call `/api/auth/refresh` server-side, swap cookies, continue.
  - Else if route is protected (everything outside `(auth)/*` and `/pricing`) → redirect to `/login?next=<path>`.
- New `frontend/lib/api.ts` fetch wrapper: relative URLs go through Next API proxy at `/api/...` so cookies attach automatically; on 401, retry once after `/api/auth/refresh`.
- Delete `frontend/lib/auth.ts` Zustand store and the `localStorage.token`/`user` reads in `useAuth.tsx`, `dashboard/page.tsx:80`, `app/admin/dashboard/page.tsx`. Replace with `useUser()` hook that reads from a server component or `/api/auth/me`.

### Components — built via `/ui-ux-pro-max:ui-ux-pro-max`
Create reusable primitives in `frontend/components/auth/`:
- `AuthCard.tsx` — centered card, brand mark, indigo glow shadow
- `OAuthButtons.tsx` — Google + Apple buttons (official brand styling, full-width, 18px radius to match iOS button radius)
- `EmailField.tsx`, `PasswordField.tsx` — Lucide icon, focus ring `ring-indigo-500/40`, `rounded-2xl`
- `PrimaryButton.tsx` — `bg-indigo-600 hover:bg-indigo-700`, `font-bold`, indigo glow shadow, loading spinner
- `Divider.tsx` — "or continue with" hairline
- `Toast` from existing pattern for resend / errors

Forms: introduce **react-hook-form + zod** (lightweight, good DX). Schema lives in `frontend/lib/auth/schemas.ts`.

### Google + Apple on web
- **Google**: `@react-oauth/google` with `<GoogleLogin>` (renders official button, returns ID token credential). POST credential to `/api/auth/google`.
- **Apple**: official "Sign in with Apple JS" loaded via `<Script>` (no good React wrapper); uses Apple Service ID + return URL. POST returned authorization code/id_token to `/api/auth/apple`.

### Visual language preserved
- Colors `slate-900` / `slate-500` / `indigo-600`, `rounded-2xl`, `font-black` headings.
- Transition: keep the existing `cubic-bezier(0.16, 1, 0.3, 1)` view-transition crossfade in `globals.css:51` between auth pages.

---

## iOS (SwiftUI)

### New SPM packages (add via Xcode)
- `GoogleSignIn-iOS` (`https://github.com/google/GoogleSignIn-iOS`)
- Apple's `AuthenticationServices` (system framework — just import, no SPM)

### Xcode project changes (`ios/Roammate.xcodeproj/project.pbxproj`)
- Add **Sign in with Apple** capability (entitlement `com.apple.developer.applesignin = ["Default"]`).
- Add URL scheme = reversed Google client ID to `Info.plist` under `CFBundleURLTypes`.
- Add `GIDClientID` key to `Info.plist`.

### View structure
```
ios/Roammate/Views/Auth/
  LoginView.swift          ← rewritten: email + "Continue with Google" + "Continue with Apple" + "Forgot password?"
  RegisterView.swift       ← rewritten: same OAuth buttons + email/password + name
  VerifyEmailView.swift    ← NEW: "Check your email", resend button, deep-link consumer
  ForgotPasswordView.swift ← NEW
  ResetPasswordView.swift  ← NEW (deep-link)
```

`LoginView` uses the existing `RoammatePrimaryButtonStyle` for the email CTA, plus:
- `SignInWithAppleButton(.signIn, onRequest:onCompletion:)` from `AuthenticationServices` — required Apple-styled button (cannot restyle).
- `GoogleSignInButton` wrapped in a `UIViewRepresentable`, sized to match.

Both buttons are full-width, `RoammateRadius.button` (18), `RoammateSpacing.md` between, with the existing spring tap animation.

### `AuthManager` extensions (`ios/Roammate/Store/AuthManager.swift`)
- `func signInWithGoogle()` — `GIDSignIn.sharedInstance.signIn(...)`, get `idToken`, POST `/auth/google`
- `func signInWithApple(authorization:)` — extract `identityToken` + `nonce`, POST `/auth/apple`
- `func signUp(email:password:name:)` — calls `/auth/signup`, transitions UI to `VerifyEmailView`
- `func verifyEmail(token:)` — called from deep-link handler
- `func refresh()` — opaque refresh token in Keychain (`KeychainHelper` extended with `saveRefreshToken`/`loadRefreshToken`); `APIClient.swift:130–150` interceptor refreshes on 401 once, otherwise emits the existing `.didReceive401` notification → logout.

### Deep links
- Universal link: `https://roammate.app/auth/verify?token=…` and `…/auth/reset?token=…` open the app via Associated Domains entitlement; backend serves `apple-app-site-association` from web.
- `RoammateApp.swift` adds `.onOpenURL { url in authManager.handleDeepLink(url) }`.

### Theme preservation
- All existing tokens reused: `Color.roammateIndigo`, `RoammateShadow.indigoGlow` on the email CTA, `RoammateRadius.button = 18`, spring `response: 0.3, dampingFraction: 0.7`, `.rounded` SF font.
- Apple/Google buttons sit above email field with a `RoammateDivider` ("or continue with email") below them.

---

## Migration & rollout

1. Apply `004_auth.sql`. All existing users keep `email_verified=false`.
2. Deploy backend with **dual login support for one release**: legacy `/users/login` returns a special response when `email_verified=false` that the new clients interpret as "go verify". (Old clients still work but get a 200 with a warning banner.)
3. Web/iOS clients are updated to: on receiving `email_verified=false`, route the user to a one-time `/auth/verify/resend` flow that emails them. After they click the link, `email_verified=true` and they continue normally.
4. After ~2 weeks, remove `/users/login` and `/users/register` and require verified email at `get_current_user`.
5. Subscription/entitlement code is untouched — `users.id` is stable.

---

## Critical files to modify or create

**Backend**
- `backend/migrations/004_auth.sql` (new)
- `backend/app/models/all_models.py` (add `email_verified`, `email_verified_at`, `auth_version`; new ORM models for `user_identities`, `email_verifications`, `password_resets`, `refresh_tokens`)
- `backend/app/services/auth/` (new package: tokens, oauth_google, oauth_apple, email, linking, templates/)
- `backend/app/api/endpoints/auth.py` (new — replaces auth bits of `users.py`)
- `backend/app/api/endpoints/users.py` (remove `/register`, `/login`; keep profile endpoints)
- `backend/app/api/router.py` (mount `/auth`)
- `backend/app/api/deps.py` (verify access token, require `email_verified`, `auth_version` check)
- `backend/app/core/config.py` + `.env.example` (Resend, Google/Apple client IDs, TTLs, cookie domain)
- `backend/requirements.txt` (`resend`, `google-auth`, `pyjwt[crypto]`, `httpx` if not present)

**Web**
- `frontend/middleware.ts` (new)
- `frontend/app/(auth)/layout.tsx` (new shared layout)
- `frontend/app/(auth)/login/page.tsx` (rewrite)
- `frontend/app/(auth)/signup/page.tsx`, `verify/page.tsx`, `verify/check/page.tsx`, `forgot/page.tsx`, `reset/page.tsx` (new)
- `frontend/app/api/auth/[...path]/route.ts` (proxy to backend, set cookies)
- `frontend/components/auth/` (AuthCard, OAuthButtons, EmailField, PasswordField, PrimaryButton, Divider — built via `/ui-ux-pro-max`)
- `frontend/lib/api.ts` (new fetch wrapper with cookie-based auth + refresh on 401)
- `frontend/lib/auth/schemas.ts` (zod schemas)
- `frontend/hooks/useAuth.tsx` (rewrite around `/api/auth/me`)
- `frontend/lib/auth.ts` (delete after callers are migrated)
- `frontend/app/dashboard/page.tsx`, `frontend/app/admin/dashboard/page.tsx`, all other `Authorization: Bearer` call sites — switch to the new `api()` wrapper
- `frontend/package.json` (add `react-hook-form`, `zod`, `@hookform/resolvers`, `@react-oauth/google`)

**iOS**
- `ios/Roammate.xcodeproj/project.pbxproj` (Sign in with Apple capability, GoogleSignIn SPM, URL types)
- `ios/Roammate/Roammate.entitlements` (new — `com.apple.developer.applesignin`, Associated Domains)
- `ios/Roammate/Info.plist` (`GIDClientID`, `CFBundleURLTypes`)
- `ios/Roammate/Views/Auth/LoginView.swift`, `RegisterView.swift` (rewrite)
- `ios/Roammate/Views/Auth/VerifyEmailView.swift`, `ForgotPasswordView.swift`, `ResetPasswordView.swift` (new)
- `ios/Roammate/Store/AuthManager.swift` (Google/Apple/refresh methods)
- `ios/Roammate/Network/APIClient.swift` (refresh-on-401 interceptor)
- `ios/Roammate/Utils/KeychainHelper.swift` (refresh token slot)
- `ios/Roammate/App/RoammateApp.swift` (`.onOpenURL` deep-link handler, `GIDSignIn.sharedInstance.handle(url)`)

---

## Verification

**Backend (pytest)**
- `tests/auth/test_signup.py`: signup creates unverified user, sends email, login is blocked until verify
- `tests/auth/test_oauth.py`: mock Google/Apple ID-token verifier; new account created; second login with same Google sub returns same user_id; auto-link when existing email is verified; blocked when not
- `tests/auth/test_refresh.py`: rotation works; reuse of consumed refresh revokes chain; `auth_version` bump invalidates all
- `tests/auth/test_password_reset.py`: token consumed once; expires after 1 hour

**Web (manual + Playwright smoke)**
- Run `pnpm dev`, hit `/signup`, complete email verification via Resend test inbox, land on `/dashboard`
- Google login from `/login` → cookies set → reload preserves session → middleware redirects unauth users from `/dashboard` to `/login?next=/dashboard`
- Apple login (requires deployed HTTPS preview — Apple won't issue tokens to localhost; test on Vercel preview)
- Forgot password → reset → login

**iOS (manual on device for Apple)**
- Sign in with Apple on a real device (simulator works for most flows but use device for Keychain reliability)
- Google sign-in via `GIDSignIn`
- Email signup → check email on device → tap universal link → app opens to verified state
- Force-quit and relaunch — session persists; expire access token → silent refresh works; expire both — user is bounced to `LoginView`

**Migration check**
- Pre-rollout: pick a current production user, confirm they hit the "verify your email" gate on next login and can resume normally afterward.

---

## Out of scope (deferred)

- 2FA / passkeys (good follow-up after verification infra exists)
- Magic-link passwordless login
- Social providers beyond Google/Apple
- Org/team accounts
- Bot/abuse rate-limiting beyond basic per-IP throttling on `/auth/*` (recommend adding in a follow-up with Redis)
