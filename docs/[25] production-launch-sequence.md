# Production Launch Sequence

Sequential playbook to take Roammate from "code merged" to "real users can sign up, sign in with Google/Apple, verify email, subscribe via Razorpay or Apple IAP, and use the iOS app on a real device." Ordered by dependency so you never get blocked waiting on a credential you need earlier.

Each phase has a clear gate ("you can move on once…") so you can pause and resume across days.

---

## Phase 0 — Decisions to lock first (5 min)

Before any setup, pin three things:

| Decision | Suggested value | Why it matters |
|---|---|---|
| Production domain | `roammate.app` (already in your code) | Apple, Google, Resend, AASA all bind to this. Don't change later. |
| Backend host | Railway (already wired via `DATABASE_URL`) | Lets you skip Docker plumbing; Postgres add-on is one click. |
| Apple Services ID | `com.roammate.app.web` | Used by Sign-in-with-Apple on the web. |

If you don't yet own `roammate.app`, buy it now from any registrar. Everything downstream needs DNS records on it.

---

## Phase 1 — Get the new code to GitHub (10 min)

```bash
cd /Users/aman.gupta1/roammate-app
git checkout -b aman/auth-refactor
git add backend frontend ios .env.example "docs/[24] auth-refactor.md"
git commit -m "Auth refactor: Google + Apple + email verification with refresh tokens"
git push -u origin aman/auth-refactor
gh pr create --title "Auth refactor: Google + Apple + email verification" --body "See docs/[24] auth-refactor.md"
```

Don't merge yet — we want Vercel to build the preview from this PR.

**Gate:** PR is open on GitHub.

---

## Phase 2 — Backend deployment first (so a real URL exists for OAuth callbacks) (30 min)

Apple and Google won't issue tokens to `localhost`, so the backend has to live at an HTTPS URL before you can finish OAuth setup.

### 2a. Railway (recommended — keeps your existing config)

1. https://railway.app → New Project → Deploy from GitHub repo → pick `roammate-app`.
2. **Root directory**: `backend`. **Builder**: Dockerfile (you have one) or Nixpacks.
3. Add a Postgres plugin → Railway auto-injects `DATABASE_URL`.
4. **Variables** (paste these now, fill in later — set blanks where noted):
   ```
   SECRET_KEY=<run: openssl rand -hex 32>
   ALLOWED_ORIGINS=https://roammate.app,https://*.vercel.app
   PUBLIC_WEB_URL=https://roammate.app
   COOKIE_DOMAIN=.roammate.app
   COOKIE_SECURE=true
   ACCESS_TOKEN_TTL_MIN=15
   REFRESH_TOKEN_TTL_DAYS=30
   APPLE_SIGNIN_BUNDLE_ID=com.roammate.app
   APPLE_SIGNIN_SERVICE_ID=com.roammate.app.web
   # filled in later phases
   RESEND_API_KEY=
   EMAIL_FROM=Roammate <auth@roammate.app>
   GOOGLE_OAUTH_CLIENT_ID_WEB=
   GOOGLE_OAUTH_CLIENT_ID_IOS=
   APPLE_SIGNIN_TEAM_ID=
   ```
5. Deploy. Once it boots, `auto_migrate.sync_schema` runs and creates the new tables automatically — but the `ALTER TABLE … NOT NULL` lines in `004_auth.sql` aren't applied by it. Run them manually:
   ```bash
   railway login
   railway link
   railway run -- psql $DATABASE_URL -f backend/migrations/004_auth.sql
   ```
6. Add a custom domain in Railway: `api.roammate.app`. Railway gives you a CNAME — add it at your registrar.

**Gate:** `curl https://api.roammate.app/health` returns `{"status":"ok"}`.

---

## Phase 3 — Vercel preview deployments (20 min)

### 3a. Connect the project

1. https://vercel.com → Add New → Project → import the same GitHub repo.
2. **Root Directory**: `frontend` (critical — your repo is a monorepo).
3. Framework preset: **Next.js**. Leave build commands at default.
4. **Environment Variables** — add to *Production*, *Preview*, and *Development*:
   ```
   NEXT_PUBLIC_API_URL=https://api.roammate.app/api
   BACKEND_INTERNAL_URL=https://api.roammate.app/api
   NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=          # fill in Phase 5
   NEXT_PUBLIC_APPLE_SIGNIN_SERVICE_ID=com.roammate.app.web
   NEXT_PUBLIC_APPLE_SIGNIN_REDIRECT_URI=https://roammate.app/api/auth/apple/callback
   NEXT_PUBLIC_GOOGLE_MAPS_MOCK=true
   ```
   For Preview, you can leave the redirect URI as `https://roammate.app/...` for now — Apple requires a verified-domain redirect, and per-preview URLs won't be allowed (workaround in Phase 6).
5. Deploy.

### 3b. Wire preview UX

- In project settings → Git → enable **Comments** so Vercel posts the preview URL on every PR.
- Settings → Domains: add `roammate.app` and `www.roammate.app` (these will go live when you merge to main; preview URLs are auto-generated per branch).
- Settings → Deployment Protection: leave **Standard Protection** on for previews (only logged-in collaborators can view), or switch to **Public** if you want shareable links.

### 3c. Preview workflow

From now on, every push to a branch with an open PR gives you `https://roammate-app-git-<branch>-<account>.vercel.app`. The Vercel bot will comment that URL on the PR. The cookie domain `.roammate.app` won't match preview URLs — for **previews**, set a separate cookie config (see "Caveat" below).

**Caveat:** previews live at `*.vercel.app`, but `COOKIE_DOMAIN=.roammate.app` won't be valid there. Either:
- **(simple)** Leave `COOKIE_DOMAIN` blank in Railway and the backend will set host-only cookies that work on both production and previews (each preview keeps its own cookie scope — fine for testing).
- **(prod-strict)** Use separate backend environments per Vercel env. Skip this until you actually need it.

Recommendation: blank `COOKIE_DOMAIN` until you're production-ready.

**Gate:** open the preview URL, hit `/login` — page renders. (OAuth won't work yet; we wire that next.)

---

## Phase 4 — Resend (fastest credential — unlocks email verification testing) (20 min)

1. https://resend.com → sign up.
2. **Add Domain** → `roammate.app`. Resend will show 3-4 DNS records (SPF TXT, DKIM CNAMEs, optional DMARC TXT). Add them at your registrar.
3. DNS propagation: 5-60 min. Refresh Resend's domain page until status = **Verified**.
4. API Keys → Create API Key → scope: Sending access → copy.
5. Set `RESEND_API_KEY` and `EMAIL_FROM=Roammate <auth@roammate.app>` in Railway and trigger a redeploy.
6. While waiting on DNS, you can test immediately by sending from `onboarding@resend.dev` (Resend's sandbox sender) — just put that in `EMAIL_FROM` temporarily.

**Gate:** `curl -X POST https://api.roammate.app/api/auth/signup -H 'content-type: application/json' -d '{"email":"you@yourdomain.com","password":"testtest12","name":"Test"}'` returns 200 and you get the verify email.

---

## Phase 5 — Google OAuth (web + iOS) (30 min)

You need **two** OAuth Client IDs from the same Google Cloud project.

### 5a. Create the GCP project

1. https://console.cloud.google.com → New Project → "Roammate".
2. APIs & Services → OAuth consent screen → External → fill in app name, support email, developer email. Add scopes: `email`, `profile`, `openid`.
3. Add yourself as a Test User (you'll only need to "Publish" the app when you want public sign-ups; for now Testing mode is fine).

### 5b. Web Client ID

1. Credentials → Create Credentials → OAuth client ID → **Web application**.
2. Authorized JavaScript origins:
   ```
   https://roammate.app
   https://www.roammate.app
   http://localhost:3000
   ```
   You can also add specific Vercel preview URLs as you create them, OR use a single wildcard via Google's "Authorized JavaScript origins" — note Google doesn't accept wildcards, so the simpler path is to test OAuth on production + localhost only.
3. Authorized redirect URIs: leave blank (Google Identity Services uses popup flow, not redirect).
4. Copy the Client ID → set both:
   - `GOOGLE_OAUTH_CLIENT_ID_WEB` in Railway
   - `NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID` in Vercel (Prod + Preview + Dev)
   - Trigger redeploys for both.

### 5c. iOS Client ID

1. Credentials → Create Credentials → OAuth client ID → **iOS**.
2. Bundle ID: `com.roammate.app`.
3. Copy the **Client ID** and the **iOS URL scheme** (reversed client ID, e.g. `com.googleusercontent.apps.123456-abc`).
4. In `ios/Roammate/App/Info.plist`, replace the two placeholders:
   - `<key>GIDClientID</key>` → `<string>123456-abc.apps.googleusercontent.com</string>`
   - URL scheme → `<string>com.googleusercontent.apps.123456-abc</string>`
5. Set `GOOGLE_OAUTH_CLIENT_ID_IOS` in Railway (backend verifies the iOS audience separately from web).

**Gate:** on the Vercel production deploy, the Google button on `/login` renders and clicking it creates a session.

---

## Phase 6 — Sign in with Apple (45 min — most fiddly)

### 6a. Apple Developer Portal

You need a paid Apple Developer Program account ($99/yr).

1. https://developer.apple.com/account → Certificates, IDs & Profiles → Identifiers.
2. Find your App ID `com.roammate.app` → Edit → check **Sign In with Apple** → Save. (This is what your `Roammate.entitlements` references.)
3. Create a **Services ID** for web:
   - Identifiers → **+** → Services IDs.
   - Description: "Roammate Web". Identifier: `com.roammate.app.web`.
   - Check **Sign In with Apple** → Configure:
     - Primary App ID: `com.roammate.app`
     - Domains and Subdomains: `roammate.app`
     - Return URLs: `https://roammate.app/api/auth/apple/callback`
     - Apple will require **domain verification** — download `apple-developer-domain-association.txt` and host it at `https://roammate.app/.well-known/apple-developer-domain-association.txt` (Next.js: drop it in `frontend/public/.well-known/`). Then click Verify.
4. Note your **Team ID** (top-right corner of the portal) → set `APPLE_SIGNIN_TEAM_ID` in Railway.

### 6b. iOS: enable the capability in Xcode

The entitlement is already in `Roammate.entitlements`, but Xcode also needs to know:
1. Open `ios/Roammate.xcodeproj` in Xcode.
2. Select the Roammate target → **Signing & Capabilities**.
3. Confirm your Team is selected and "Sign in with Apple" capability is listed (it should be, since the entitlement file is wired). If not, click + → add it.
4. While here, also confirm **Associated Domains** shows `applinks:roammate.app`.

### 6c. Preview-environment limitation

Apple Sign-in only works at the exact `Return URL` you registered — i.e. `https://roammate.app`. It will **not** work on Vercel preview URLs. To test on previews:
- Either skip Apple on previews (Google + email still work), or
- Register a separate Services ID (`com.roammate.app.preview`) with a wildcard-ish return URL pointing to a stable preview-router domain. Most teams just test Apple on production.

**Gate:** Apple button on the production `/login` renders and signs you in.

---

## Phase 7 — Apple IAP (subscription) (45 min, lots of waiting)

### 7a. App Store Connect

1. https://appstoreconnect.apple.com — sign Paid Applications agreement (Agreements, Tax, and Banking → fill in bank + tax forms). This takes 1-3 business days to be "Active." You can configure products in the meantime.
2. **Add App** → bundle `com.roammate.app` → fill required fields. You don't need to submit for review yet.
3. **Features → In-App Purchases → +**:
   - Type: **Auto-Renewable Subscription**.
   - Reference Name: "Roammate Plus Monthly".
   - Product ID: `com.roammate.app.plus.monthly` (matches `APPLE_IAP_PRODUCT_ID_MONTHLY` in your config).
   - Create a **Subscription Group**: "Roammate Plus".
   - Subscription Duration: 1 Month. Price: ₹149 (or your tier).
   - Localizations: at least English display name + description.
   - Review notes + screenshot required.
4. (Optional) Create the one-time product `com.roammate.app.plus.onetime` (Non-Consumable) at ₹200.

### 7b. App Store Server API key (for renewal webhooks)

1. Users and Access → Integrations → In-App Purchase → Generate API Key.
2. Download the `.p8`, note Key ID + Issuer ID.
3. Set `APPLE_ISSUER_ID`, `APPLE_KEY_ID`, and place the .p8 contents in Railway (use `APPLE_PRIVATE_KEY_PATH` to a Railway-mounted file or inline as an env var depending on your code — check `app/services/payments/apple.py`).

### 7c. Sandbox testers

1. Users and Access → **Sandbox** → Testers → +.
2. Create an email you don't use for real Apple ID (e.g. `aman+sandbox1@yourdomain.com`). Set a password. Don't verify it through email — just use it.
3. On your real iPhone: Settings → App Store → Sandbox Account → sign in with that tester.

**Gate:** product `com.roammate.app.plus.monthly` shows status "Ready to Submit" in App Store Connect, sandbox tester exists.

---

## Phase 8 — Razorpay (30 min)

### 8a. Account + test plan

1. https://dashboard.razorpay.com → sign up. Stay in **Test Mode**.
2. Settings → API Keys → Generate Test Keys → copy Key ID + Secret.
3. Subscriptions → Plans → Create Plan:
   - Period: Monthly, Interval: 1, Amount: ₹149.
   - Copy the `plan_…` ID.
4. Settings → Webhooks → +:
   - URL: `https://api.roammate.app/api/billing/razorpay/webhook` (use your Railway URL).
   - Active events: `subscription.activated`, `subscription.charged`, `subscription.cancelled`, `payment.captured`, `payment.failed`.
   - Generate a webhook secret → copy.
5. Set in Railway:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxx
   RAZORPAY_KEY_SECRET=xxx
   RAZORPAY_WEBHOOK_SECRET=xxx
   RAZORPAY_PLAN_ID_MONTHLY=plan_xxx
   ```
6. In Vercel: `NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_xxx`.

### 8b. Local webhook testing (optional, only if you want to test before deploy)

```bash
brew install ngrok
ngrok http 8000
# copy https URL into Razorpay webhook field temporarily
```

**Gate:** Test card `4111 1111 1111 1111` / any future expiry / CVV `123` on `/pricing` completes a subscription and webhook flips your user to `subscription_tier=plus`.

---

## Phase 9 — Finish iOS Xcode wiring (15 min)

### 9a. Add GoogleSignIn SPM

1. Xcode → File → **Add Package Dependencies**.
2. URL: `https://github.com/google/GoogleSignIn-iOS`.
3. Dependency Rule: Up to Next Major Version → 7.0.0.
4. Add to target: select both `GoogleSignIn` and `GoogleSignInSwift`. Click Add Package.

### 9b. Verify signing

1. Target → Signing & Capabilities → Team: your Apple Developer team.
2. Automatically manage signing: ON.
3. Capabilities you should see:
   - Sign in with Apple
   - Associated Domains (`applinks:roammate.app`)
   - In-App Purchase (already there)
4. If anything's missing, click **+** to add.

### 9c. StoreKit local config (for sandbox-free local IAP testing)

1. Edit Scheme (⌘<) → Run → Options.
2. StoreKit Configuration: select `Subscription/RoammatePlus.storekit`.
3. Now when you run on simulator, purchases use the local synthetic StoreKit and don't need a real sandbox tester.

**Gate:** project builds (⌘B). Run on simulator (⌘R), tap Apple button → should at least surface the Apple system sheet (it won't fully sign in on simulator, but the button works).

---

## Phase 10 — Real-device iOS testing (30 min — first time)

### 10a. One-time device trust

1. Plug your iPhone into your Mac.
2. iPhone: unlock, tap "Trust" on the popup.
3. Mac: Xcode → Window → Devices and Simulators → wait for your device to appear, no exclamation marks.
4. Top-bar device picker in Xcode → select your physical iPhone.
5. Build & Run (⌘R).
6. First run will fail with "Untrusted Developer." On iPhone: Settings → General → VPN & Device Management → tap your dev cert → Trust.
7. Re-run from Xcode.

### 10b. Pointing the iOS app at your backend

The app reads `API_BASE_URL` env var in DEBUG, else falls back to `https://api.roammate.app`. Two options:

- **Easy**: point to Railway. Edit Scheme → Run → Arguments → Environment Variables: `API_BASE_URL = https://api.roammate.app/api`. Restart app. This is what you want for a real end-to-end test.
- **Local backend**: run the backend locally, get your Mac's LAN IP (`ipconfig getifaddr en0`), set `API_BASE_URL = http://192.168.x.x:8000/api`, and add `NSAppTransportSecurity` exception (you already allow local networking). Phone + Mac must be on the same Wi-Fi.

### 10c. Real-device gotchas

- **Sign in with Apple** only fully works on a real device with a real Apple ID. On simulator it'll cancel.
- **Universal links** (`/verify`, `/reset` deep links) only work on a real device after AASA is hosted (Phase 11).
- **Sandbox IAP**: in Settings → App Store → Sandbox Account, sign in as the tester from Phase 7c. Now in-app purchases run against sandbox.
- **Push notifications** (not in scope here, but FYI): also require real device.

**Gate:** real device opens app → sign in with Apple → land on dashboard.

---

## Phase 11 — Universal links (the deep-link gate) (30 min, mostly waiting on Apple)

This is what makes `https://roammate.app/verify?token=...` from the verification email open your iOS app instead of Safari.

### 11a. Host the AASA file

1. Create `frontend/public/.well-known/apple-app-site-association` (no `.json` extension!):
   ```json
   {
     "applinks": {
       "details": [
         {
           "appIDs": ["YOUR_TEAM_ID.com.roammate.app"],
           "components": [
             { "/": "/verify",       "comment": "Email verification deep link" },
             { "/": "/reset",        "comment": "Password reset deep link" },
             { "/": "/auth/verify*", "comment": "Legacy paths" },
             { "/": "/auth/reset*",  "comment": "Legacy paths" }
           ]
         }
       ]
     }
   }
   ```
   Replace `YOUR_TEAM_ID` with the 10-char team ID from Phase 6a.
2. Add a Vercel route override so it's served with `Content-Type: application/json` even without an extension. In `frontend/next.config.js` add:
   ```js
   async headers() {
     return [
       {
         source: '/.well-known/apple-app-site-association',
         headers: [{ key: 'Content-Type', value: 'application/json' }],
       },
     ];
   }
   ```
3. Push, let Vercel deploy.
4. Validate: `curl -I https://roammate.app/.well-known/apple-app-site-association` → 200, content-type json, no redirect.
5. Test in Apple's debugger: https://search.developer.apple.com/appsearch-validation-tool/

### 11b. App-side

Already done in `RoammateApp.swift` (`.onOpenURL`) + `Roammate.entitlements` (`applinks:roammate.app`). Apple's `swcd` daemon on the device may take up to 24h to pick up the AASA — first install of the app after AASA goes live usually works immediately.

**Gate:** sign up a fresh account on iOS → receive email → tap link → app opens to verified state.

---

## Phase 12 — End-to-end smoke (1 hour)

Walk through every path. Mark each ✓:

**Auth (web, production)**
- [ ] `/signup` with new email → verify email arrives → click link → land on `/dashboard`
- [ ] `/login` with verified user → land on `/dashboard`
- [ ] `/login` with Google → land on `/dashboard`
- [ ] `/login` with Apple → land on `/dashboard` (test once, this is the riskiest one)
- [ ] `/forgot` → reset email arrives → click → set new password → logged in
- [ ] Close tab, reopen `/dashboard` → still logged in (cookie persistence)
- [ ] Wait 16 minutes → make an API call → silent refresh works (DevTools → Application → Cookies → `rm_access` should have a fresh expiry)
- [ ] Log out → `/dashboard` redirects to `/login?next=/dashboard`

**Auth (iOS, real device)**
- [ ] Sign up → "check your email" sheet → tap link in Mail → app opens, signed in
- [ ] Sign in with Apple → land on dashboard
- [ ] Sign in with Google → land on dashboard
- [ ] Forgot password → email → tap link → reset sheet opens in app → new password works
- [ ] Force-quit app → relaunch → still signed in
- [ ] Logout → returns to LoginView

**Subscription (web, Razorpay test mode)**
- [ ] `/pricing` → Subscribe → Razorpay opens → test card → success
- [ ] Profile shows Plus
- [ ] Refresh `/api/auth/me` shows tier change
- [ ] Webhook in Railway logs shows event received

**Subscription (iOS, sandbox)**
- [ ] In-app purchase sheet appears → confirm → confetti + Plus banner
- [ ] Backend `subscription_tier` flips to `plus`
- [ ] Cross-platform check: log into the same account on web — Plus is reflected

**Account linking**
- [ ] Sign up with email A + verify
- [ ] Log out, "Sign in with Google" using the same email A → lands on existing account (auto-linked)
- [ ] In profile → linked identities shows Google attached

---

## Sequencing summary (TL;DR)

```
1.  Buy domain                          (5 min)
2.  Push branch + open PR               (10 min)
3.  Deploy backend to Railway           (30 min)
4.  Connect Vercel, deploy preview      (20 min)
5.  Resend domain verify + API key      (20 min + DNS wait)
6.  Google OAuth client IDs             (30 min)
7.  Apple Services ID + iOS capability  (45 min)
8.  Apple IAP product + sandbox tester  (45 min + agreement wait)
9.  Razorpay test plan + webhook        (30 min)
10. Xcode: add GoogleSignIn SPM         (15 min)
11. Real-device run                     (30 min, first time)
12. AASA universal-links file           (30 min)
13. Smoke test everything               (60 min)
```

Total active work: ~6 hours. Wall-clock with DNS + Apple agreement waits: 2-3 days.

**The thing to start in parallel right now:** Apple's "Paid Applications" agreement (Phase 7a). That has a 1-3 day clock and gates IAP testing entirely. Submit it before anything else and the wait runs in the background while you do everything else.
