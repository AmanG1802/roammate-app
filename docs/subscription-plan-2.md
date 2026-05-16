# Roammate Subscription Feature — Implementation Plan

## Context

Roammate currently runs as an all-free product with no monetization. The AI concierge and brainstorm features dominate variable cost (LLM tokens tracked in `TokenUsage` already). To convert the product into a sustainable business, we are introducing **Roammate Plus**, a paid tier — India-first, monthly billing at **₹149/month** (annual deferred to v2). A free tier remains so users can experience value before paying (soft paywall after value).

This plan covers backend entitlement enforcement, **Razorpay (web/Android)** + **Apple IAP / StoreKit 2 (iOS)** integration, and the frontend hooks needed for the `/ui-ux-pro-max:ui-ux-pro-max` skill to design paywall + onboarding screens in Next.js and SwiftUI.

---

## Tier Matrix

| Capability | Free | Plus (₹149/mo) |
|---|---|---|
| Active trips (upcoming, `end_date >= today`) | **2** | Unlimited |
| Past trips (read-only history) | Unlimited (read-only) | Unlimited (full) |
| Brainstorm AI messages | **15 / calendar month / user** | Unlimited |
| Concierge chat | **Blocked** (full feature gate) | Unlimited |
| Trip collaboration (invite members) | Allowed (caps apply) | Allowed |
| Maps (Apple Maps, routes, pins) | Online only | **Offline cache** |
| LLM model | Standard | Standard (model parity for v1) |
| Branded PDF / share exports | Basic | Basic (no gating in v1) |

Downgrade behavior (per user choice): **hard enforce free limits on cancellation / failed payment**. Active trips beyond 2 become read-only until user archives or re-subscribes; concierge fully locks (history readable but `POST /chat` returns 402).

---

## Architecture

### 1. Data Model (backend)

Add to `backend/app/models/all_models.py` (`User` table area):

```python
# On User
subscription_tier: Mapped[str] = mapped_column(String(16), default="free")  # "free" | "plus"
subscription_status: Mapped[str] = mapped_column(String(24), default="none")
  # "none" | "active" | "past_due" | "canceled" | "expired"
subscription_provider: Mapped[str | None]   # "razorpay" | "apple"
subscription_current_period_end: Mapped[datetime | None]
subscription_external_id: Mapped[str | None]  # Razorpay sub_id or Apple originalTransactionId

# New table: SubscriptionEvent (audit log)
class SubscriptionEvent(Base):
    id, user_id, provider, event_type, raw_payload (JSONB), created_at

# New table: UsageCounter (monthly quota)
class UsageCounter(Base):
    user_id, period (YYYY-MM), brainstorm_messages: int
    # Concierge has no counter — feature-gated entirely
```

Alembic migration required.

### 2. Entitlement Service (backend)

New file: `backend/app/services/entitlements.py`

- `get_entitlement(user) -> Entitlement` — returns dataclass with effective flags:
  `can_create_active_trip`, `can_use_concierge`, `brainstorm_remaining`, `tier`, `status`, `period_end`.
- `enforce_or_raise(user, feature)` — raises `HTTPException(402, detail={"code": "needs_plus", "feature": …})`.
- `bump_brainstorm_counter(user)` — atomic increment with upsert.
- Active-trip check uses existing query in `trips.py:36–62` filtered by `start_date/end_date`.

### 3. Endpoint Gating

| Endpoint | Gate |
|---|---|
| `POST /trips` (create) | If new trip's `end_date >= today` AND user already has 2 active trips on free → 402 `needs_plus:active_trips` |
| `POST /trips/{id}/brainstorm/chat` | If free + counter ≥ 15 → 402 `needs_plus:brainstorm_quota`. On success, increment counter |
| `POST /trips/{id}/concierge/chat` | If free → 402 `needs_plus:concierge` |
| `GET /trips/{id}/concierge/messages` | Allowed (read-only history visible) |

Files: `backend/app/api/endpoints/trips.py`, `brainstorm.py:123-179`, `concierge.py:173-228`.

### 4. Payments — Razorpay (web / future Android)

New file: `backend/app/services/payments/razorpay_service.py`

- Razorpay **Subscriptions API** with **e-mandate / UPI AutoPay** plan (recurring monthly).
- One Plan: `roammate_plus_monthly_inr` (₹149).
- Endpoints in new `backend/app/api/endpoints/billing.py`:
  - `POST /billing/razorpay/subscription` → creates Razorpay subscription, returns `subscription_id` + Razorpay Checkout config (key, sub_id, name, prefill).
  - `POST /billing/razorpay/webhook` → verifies HMAC, handles `subscription.activated`, `subscription.charged`, `subscription.halted`, `subscription.cancelled`, `payment.failed`. Idempotent via `SubscriptionEvent.event_id`.
  - `POST /billing/cancel` → `subscription.cancel(at_cycle_end=true)`.
  - `GET /billing/status` → returns current entitlement DTO for clients.

Env additions in `backend/app/core/config.py`:
`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `RAZORPAY_PLAN_ID_MONTHLY`.

### 5. Payments — Apple IAP (iOS)

- Auto-renewable subscription in App Store Connect, group `roammate_plus`, product ID `com.roammate.app.plus.monthly`. Apple-set ₹149 price tier.
- Add **In-App Purchase capability** + entitlements file in `ios/Roammate.xcodeproj`.
- New iOS module: `ios/Roammate/Subscription/`:
  - `StoreKitClient.swift` — StoreKit 2 `Product.products(for:)`, `purchase()`, `Transaction.updates` listener, `currentEntitlements` check.
  - `SubscriptionStore.swift` — `ObservableObject`, `@Published var entitlement: Entitlement`, syncs with backend.
- After a successful StoreKit transaction, the app calls `POST /billing/apple/verify` with the JWS `signedTransactionInfo`. Backend verifies via Apple's JWS public keys, links `originalTransactionId` → `User`, sets tier.
- Backend also accepts **App Store Server Notifications V2** at `POST /billing/apple/webhook` for renewals/expirations/refunds (Apple → backend ground truth).

Env: `APPLE_BUNDLE_ID`, `APPLE_SHARED_SECRET` (legacy unneeded for JWS but keep), `APPLE_ISSUER_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` (for App Store Server API lookups).

---

## Design Language (must match existing app)

All paywall, profile, and onboarding surfaces inherit Roammate's existing system. **Do not introduce new colors, fonts, or motion curves.**

**Brand tokens (iOS — `Theme/RoammateTheme.swift`; Web — Tailwind defaults):**

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| Indigo (primary) | `#4F46E5` | `indigo-600` | Primary CTA, Plus brand color, focus states |
| Indigo Dark | `#4338CA` | `indigo-700` | Pressed CTA, hover |
| Indigo Tint | `#EDE9FE` | `indigo-50` | Plus badges, paywall card backgrounds, selection chips |
| Ink (text primary) | `#0F172A` | `slate-900` | Headlines |
| Muted (text secondary) | `#64748B` | `slate-500` | Body, descriptions |
| Background | `#F8FAFC` | `slate-50` | Page bg |
| Border | `#E2E8F0` | `slate-200` | Card borders, dividers |
| Success | `#10B981` | `emerald-500` | "Subscribed" status, success toast |
| Danger | `#F43F5E` | `rose-500` | Cancel destructive, payment failed |
| Amber Accent | `#F59E0B` | `amber-500` | "Plus" sparkle highlight, upgrade nudge dots |

**Plus brand visual**: an **indigo → fuchsia → amber linear gradient** (`#4F46E5 → #D946EF → #F59E0B`) reserved exclusively for the Plus crest, paywall hero, and the "Roammate Plus" wordmark. This gradient never appears on free-tier surfaces — it's the visual cue users learn to associate with the upgrade.

**Type**: SF Pro Rounded on iOS (`.system(design: .rounded)`); web uses system stack with `font-black` for titles, `font-semibold` for CTAs, `tracking-tight` on display sizes. The "Roammate Plus" wordmark is always `title2/text-2xl, weight black, design rounded` with the brand gradient as foreground.

**Spacing/radius (iOS)**: `RoammateSpacing.md=16, lg=24, xl=32`; `RoammateRadius.card=32, button=18, pill=999`. **Web**: `rounded-2xl` for cards, `rounded-xl` for menu rows, `rounded-full` for pills.

**Shadows**: iOS — `RoammateShadow.card` (indigo @ 8%) on paywall card; `indigoGlow` on the subscribe CTA. Web — `shadow-sm` baseline, `shadow-[0_8px_24px_-8px_rgba(79,70,229,0.35)]` on the primary subscribe button.

**Motion library — use what's already in the app, do not introduce new easings:**

| Pattern | iOS | Web |
|---|---|---|
| Sheet/drawer open | `.spring(response: 0.35, dampingFraction: 0.85)` | Framer `transition={{ duration: 0.22, ease: 'easeOut' }}` from `{ opacity: 0, y: 8 }` |
| Button press | `scale 0.98`, `.spring(0.3, 0.7)` | `whileTap={{ scale: 0.97 }}` |
| Selection (plan card) | `.spring(0.35, 0.85)` scale 1.0→1.03 + indigo border in | `scale-105` + `border-2 border-indigo-600` with `transition-all duration-200` |
| Stagger grid entry | matchedGeometryEffect + `0.04s * index` delay | `delay: idx * 0.04, duration: 0.18` |
| Plus crest "shimmer" | `TimelineView(.animation)` + hue rotation 0→8° loop, 4s | CSS `@keyframes` linear-gradient angle 0→360°, 8s `expo` ease |
| Confetti on subscribe-success | SwiftUI `Canvas` 24-particle burst, 1.2s | Framer Motion 24 `motion.span` with stagger and `expo` cubic-bezier |
| Hit-paywall sheet entry | `.move(edge: .bottom)` + opacity, spring | Framer `AnimatePresence` slide-up + dim overlay, 260ms |

**Iconography**: SF Symbols on iOS (`sparkles`, `crown.fill`, `infinity`, `map.fill`, `wand.and.stars`); Lucide on web (`Sparkles`, `Crown`, `Infinity`, `Map`, `Wand2`).

---

## 6. Web App (Next.js + Tailwind + Framer Motion)

### 6.1 Subscription menu in Profile (`frontend/app/profile/`)

Existing structure (`profile/layout.tsx:12`): left rail nav with menu rows styled `bg-indigo-50 text-indigo-700 border-l-[3px] border-indigo-600` when active. Subscription is currently a "Soon" stub.

**Changes:**

- **`profile/layout.tsx`** — remove "Soon" badge. For **free users**, replace it with an amber pill `Upgrade` (text-[10px], `bg-amber-50 text-amber-700`, subtle pulse animation `@keyframes pulse-soft` 2s). For **Plus users**, render a gradient `Plus` pill (the indigo→fuchsia→amber gradient as text via `bg-clip-text`).
- **`profile/subscription/page.tsx`** — full rewrite. Two states:

  **State A — Free user (upsell surface):**
  ```
  ┌─ Card 1: Plus Hero ────────────────────────────────────┐
  │  [animated gradient crest 56×56]                       │
  │  Roammate Plus                                         │
  │  Unlimited concierge. Offline maps. Built for travelers│
  │  who actually go places.                               │
  │                                                        │
  │  ₹149 / month   [ Subscribe →  shadow-indigo glow ]    │
  │  Billed monthly via UPI or card. Cancel anytime.       │
  └────────────────────────────────────────────────────────┘
  ┌─ Card 2: Tier Comparison (2 columns, 4 rows) ──────────┐
  │              Free          Plus                        │
  │  Trips       2 active      ∞                           │
  │  Brainstorm  15 / month    ∞                           │
  │  Concierge   —             ✓                           │
  │  Offline maps —            ✓                           │
  └────────────────────────────────────────────────────────┘
  ┌─ Card 3: FAQ accordion ────────────────────────────────┐
  ```
  - Hero card: white bg, `rounded-2xl border border-slate-100`, `p-8`. Crest: 56×56 `rounded-2xl` with the brand gradient and a subtle 8s rotating conic-gradient overlay.
  - Subscribe button: full-width on mobile, fit-content on md+. Indigo-600, white text, font-semibold, `rounded-full px-6 py-3`, `shadow-[0_8px_24px_-8px_rgba(79,70,229,0.45)]`, `whileTap={{ scale: 0.97 }}`. Triggers Razorpay Checkout.
  - Comparison table animates in row-by-row with `0.06s` stagger using Framer.

  **State B — Plus user (management surface):**
  ```
  ┌─ Status banner ────────────────────────────────────────┐
  │  [crown.fill in gradient]  You're on Roammate Plus     │
  │  Renews on 14 Jun 2026 · ₹149/month · UPI ••• 4321     │
  └────────────────────────────────────────────────────────┘
  ┌─ Usage this month ─────────────────────────────────────┐
  │  Brainstorms ∞        Concierge messages: 48           │
  │  Active trips: 5      Offline maps: enabled            │
  └────────────────────────────────────────────────────────┘
  ┌─ Manage ───────────────────────────────────────────────┐
  │  > Update payment method                               │
  │  > Download invoices                                   │
  │  > Cancel subscription            (text-rose-600)      │
  └────────────────────────────────────────────────────────┘
  ```
  - Status banner uses `bg-gradient-to-r from-indigo-50 via-fuchsia-50 to-amber-50` with `border border-indigo-100`.
  - Cancel triggers a confirmation modal (reuses existing modal pattern from `OnboardingPersonaModal.tsx`): "You'll keep Plus until 14 Jun. After that, trips beyond 2 become read-only and concierge will lock."

### 6.2 Standalone pricing page (`frontend/app/pricing/page.tsx`, new)

Public marketing-style page for SEO and external referrals. Hero with the gradient crest, big "₹149/month" price, tier matrix (reuses comparison component), "Subscribe" CTA — same Razorpay flow as in-app, but signed-out users route to `/login?next=/profile/subscription` first.

GSAP `expo.out` on hero entry (matches existing landing patterns); rest uses Framer.

### 6.3 Paywall modal (`frontend/components/PaywallModal.tsx`, new)

A single component, contextual copy keyed off the `feature` code from a 402 response.

- Rendered through a `PaywallProvider` context at the root layout. `useEntitlement().requirePlus(feature)` returns a promise that opens the sheet.
- Layout: centered card 480px wide, `bg-white rounded-3xl shadow-2xl`, framed by a 1px gradient border (`bg-clip-padding` trick with the brand gradient).
- Entry: backdrop fades 200ms, card slides up 24px + opacity over 260ms with `expo` cubic-bezier. Exit reverses, 180ms.
- Header has a feature-specific icon (Lucide), title, and a one-line context message:

  | `feature` code | Title | Subtext |
  |---|---|---|
  | `concierge` | "Meet your trip concierge" | "Always-on AI travel companion — included with Plus." |
  | `brainstorm_quota` | "You've used 15 brainstorms this month" | "Go unlimited with Plus, or wait until 1st of next month." |
  | `active_trips` | "You're planning 2 trips already" | "Plus lifts the cap so you can dream as wide as you travel." |
  | `offline_maps` | "Take your maps off-grid" | "Offline tiles + saved pins for when signal disappears." |

- Footer: `Subscribe for ₹149/mo` (primary) + `Maybe later` (ghost). Subscribing launches Razorpay Checkout inline without unmounting the modal; on success, modal swaps to a confetti success state (Framer staggered burst), then auto-closes after 2.5s and re-fires the original action that triggered the paywall.

### 6.4 Entitlement hook (`frontend/hooks/useEntitlement.ts`, new)

```ts
const { tier, status, periodEnd, brainstormRemaining, canUseConcierge,
        requirePlus } = useEntitlement();
```

- Hydrated from `GET /billing/status` at app boot and after any successful checkout.
- `requirePlus(feature)` opens the PaywallModal; resolves on success.
- Components consume it to render contextual hints: greyed-out concierge tab with `Plus` pill, "12 / 15 brainstorms this month" counter in the brainstorm pane, etc.

### 6.5 Free-tier UI affordances throughout the app

Tiny, persistent nudges that build awareness without nagging:

- **Brainstorm pane**: thin pill below the input — `4 brainstorms left this month` (turns amber at ≤3, rose at 0).
- **Concierge tab in trip view**: shows a locked state with the gradient crest and a single line "Concierge is a Plus feature" + small Subscribe CTA. No empty-promise "coming soon" anymore.
- **Trip list**: when at 2/2 active trips, the "+ New trip" button gets a small `Plus` indigo-tinted badge; tapping opens paywall.
- **Map view**: an "Offline" toggle in the map controls — for free, tapping shows a tiny tooltip "Plus feature" with the upgrade CTA. No modal interruption unless they explicitly tap "Upgrade".

### 6.6 Onboarding workflow (web)

Triggered from the existing `OnboardingPersonaModal.tsx` flow after persona selection. Adds **two new steps** before dropping users on the dashboard:

**Step A — "Here's what you can do free"** (no card, 4s read):
- Three animated cards stagger in (0.08s delay): "Plan 2 trips at a time", "15 AI brainstorms each month", "Visual map planning".
- CTA: `Start planning`.

**Step B — "Try Plus on us" (optional, soft, no card required)**:
- Heading: "Want the full Roammate?"
- Bullet list of Plus features with check-circles animating in (0.1s stagger, `expo` ease):
  - ✓ Unlimited brainstorms
  - ✓ Always-on AI concierge
  - ✓ Offline maps & pins
- Two CTAs: `See pricing` (routes to `/pricing`) + `Maybe later` (continues to dashboard).
- **Important**: no card capture, no trial. The choice is "consider Plus" vs. "start free." This is intentional given the user's choice of soft-paywall-after-value over reverse-trial.

**Re-engagement nudge** (lightweight, dismissible) — shown once on the dashboard the *3rd time* a free user opens the app: a thin top banner "You've planned 1 trip — ready to unlock the concierge?" with `Try Plus` and a dismiss × . Local-storage flag, never re-shown.

---

## 7. iOS App (SwiftUI + StoreKit 2)

### 7.1 Subscription menu in Profile (`ios/Roammate/Views/Profile/`)

Existing `ProfileTabView.swift` already has a settings-row list with SF Symbol icons in 44×44 indigo-tinted squares. **The "Subscription" row stays in the same position** but its appearance changes by tier:

- **Free user**: leading icon = `sparkles` in the **brand gradient** square (not flat indigo) — visually distinct from other rows. Trailing text: `Upgrade` in amber-500. Subtle 2s pulse opacity 0.7→1.0 loop on the gradient.
- **Plus user**: leading icon = `crown.fill` in gradient square. Trailing text: `Plus` in a gradient-filled pill.

Tapping pushes `SubscriptionView` (replaces the existing stub).

### 7.2 `SubscriptionView.swift` rewrite

Two states matching the web design.

**Free state — paywall hero:**
- Top hero: 96×96 gradient crest (`AngularGradient` with the indigo→fuchsia→amber stops) with a `TimelineView(.animation)` rotating the angle slowly (8s cycle, paused if reduce-motion is on).
- Title "Roammate Plus" in `.system(.largeTitle, design: .rounded, weight: .black)` with the gradient as foreground via `.foregroundStyle(LinearGradient(...))`.
- Tagline (subheadline, muted).
- **Price card** (`RoammateCardModifier`): `₹149 / month`, supporting line "Billed monthly. Cancel anytime."
- **Tier comparison list** — 4 rows, each a `HStack` with feature icon, label, and two checkmark/dash columns. Rows fade-in with `.transition(.asymmetric(insertion: .move(edge: .bottom).combined(with: .opacity), removal: .opacity))` and 0.06s stagger using `.task` + `Task.sleep`.
- **Subscribe CTA** (`RoammatePrimaryButtonStyle`): full-width, capsule, indigo bg, white text, `RoammateShadow.indigoGlow`. `scaleEffect(isPressed ? 0.97 : 1.0)` with the standard spring. Tapping calls `subscriptionStore.purchase()`.
- **Footer**: "Restore Purchases" (text button), legal links (Terms, Privacy), and a small line "Subscriptions auto-renew. Manage anytime in Settings → Apple ID." (App Store policy compliance text — required.)

**Plus state — management:**
- Status header: gradient crest + "You're on Plus", "Renews 14 Jun 2026".
- Card: "Manage Subscription" — tapping opens `UIApplication.shared.open(URL(string: "itms-apps://apps.apple.com/account/subscriptions"))` (App Store policy: must redirect to Apple, cannot self-cancel iOS subs).
- Usage card mirrors web.
- No "Cancel" button (Apple owns cancel UX for IAP subs).

### 7.3 Paywall sheet (`Views/Paywall/PaywallSheet.swift`, new)

`.sheet(isPresented:)` with `.presentationDetents([.fraction(0.7), .large])` and `.presentationDragIndicator(.visible)`.

- Same contextual `feature` keying as web: `concierge | brainstorm_quota | active_trips | offline_maps`.
- Layout: gradient crest at top (smaller, 64×64), title, subtext, feature highlights (3 SF Symbol rows), price line, Subscribe CTA, "Not now" ghost.
- Entry: standard sheet, `.spring(response: 0.35, dampingFraction: 0.85)`.
- Success state: replaces content with a `Canvas`-driven 24-particle confetti burst (gradient stops as particle colors) over 1.2s, then auto-dismisses.

### 7.4 `SubscriptionStore.swift` and `StoreKitClient.swift`

- `StoreKitClient`: fetches `Product.products(for: ["com.roammate.app.plus.monthly"])`, runs `Transaction.updates` listener, validates entitlements on app boot.
- `SubscriptionStore: ObservableObject`:
  - `@Published var entitlement: Entitlement`
  - `purchase()` → StoreKit purchase → on `.success(verified)`, POST `signedTransactionInfo` to `/billing/apple/verify` → refresh entitlement from `/billing/status`.
  - `restorePurchases()` → `Transaction.currentEntitlements` + backend sync.
- Wired into `AuthManager` boot so the tab bar, paywall sheets, and inline nudges all read from one source.

### 7.5 `APIClient.swift` extension (`:164-168`)

- Add `case paymentRequired(feature: String)` to `APIError`.
- Decode 402 body `{"code":"needs_plus","feature":"concierge"}` → `.paymentRequired("concierge")`.
- Post a `Notification.Name.needsPlus` with the `feature` in `userInfo`.
- A root-level view modifier `.observePaywall()` (new) listens for this notification and presents `PaywallSheet`. Mounted once on `ContentView`.

### 7.6 Free-tier UI affordances throughout the iOS app

- **`BrainstormPaneView.swift`**: small pill above the input — gradient text "4 left this month", color shifts amber→rose as quota depletes.
- **`TripConciergeView.swift`**: replace placeholder with a permanent "locked" state for free users — large gradient crest, "Concierge is a Plus feature", `Try Plus` button. Plus users get the real chat UI.
- **`CreateTripView.swift`**: free user with 2 active trips + future `endDate` → on Save, intercept and present `PaywallSheet(feature: "active_trips")` instead of calling the API. Cleaner UX than waiting for a 402.
- **Trip list `+` button**: when at 2/2, a small gradient dot overlays the FAB to hint at the cap.
- **Map controls (`PlanMapPage.swift`)**: an "Offline" toggle in the map control bar; for free users, tapping it shows a small `popover` tip with `Try Plus` (no full sheet — micro-friction only).

### 7.7 Onboarding workflow (iOS)

Add to the existing post-signup flow (after persona selection in `Views/Auth/` or onboarding screens):

**Screen A — "Here's what you can do free"**
- Three cards in a `VStack` with `matchedGeometryEffect` fade-in (0.08s stagger).
- Card style: white bg, `RoammateCardModifier`, SF Symbol icon in indigo-tinted square.
- CTA: `Start planning` (RoammatePrimaryButtonStyle).

**Screen B — "Want the full Roammate?" (skippable)**
- Same content as web Step B. Three feature rows with check-circle.fill in emerald.
- CTAs: `See Plus` (pushes `SubscriptionView`) + `Maybe later` (dismisses onboarding).

**Re-engagement nudge** — a small banner on the trip list, shown on the 3rd app open if user is still free and has created ≥1 trip. Tracked via `@AppStorage("plusNudgeShown")`. One-time, dismissible.

### 7.8 Animation specifics (iOS)

- Plus crest "shimmer": `TimelineView(.animation)` driving `AngularGradient(angle: .degrees(date.elapsed * 45))` (8s full rotation), paused under reduce-motion via `@Environment(\.accessibilityReduceMotion)`.
- Tier comparison rows: appear with `0.06s * index` Task.sleep delay; each row uses `.transition(.asymmetric(...))`. Wrap the entire list in a single `withAnimation(.spring(response: 0.35, dampingFraction: 0.85))` on `isVisible` toggle.
- Subscribe success confetti: 24 particles, each `Capsule` rotated random, gradient colors picked from {indigo, fuchsia, amber}, animated via `withAnimation(.spring(response: 0.6, dampingFraction: 0.4))` over 1.2s with random offsets.
- All button presses inherit `RoammateRowButtonStyle` / `RoammatePrimaryButtonStyle` — no new motion curves introduced.

---

## 8. Onboarding & Conversion Funnel (combined)

End-to-end journey designed to maximize value-before-payment while keeping subscription always one tap away.

| Stage | Trigger | Surface | Goal |
|---|---|---|---|
| 0. Signup | Register | Auth → persona modal (existing) | Identify user |
| 1. Free-tier explainer | Right after persona | Onboarding Screen A (3 cards) | Set expectations on what free includes |
| 2. Plus tease | Onboarding Screen B (skippable) | Soft pitch, no card asked | Plant the seed |
| 3. First value | User creates Trip 1, runs first brainstorm | No paywall | Habit formation |
| 4. Contextual paywall | Tap Concierge / 16th brainstorm / 3rd active trip / Offline maps | `PaywallSheet` keyed to feature | Convert at peak intent |
| 5. Ambient nudges | Brainstorm counter pill, locked concierge tab, Plus pill on profile row | Persistent low-friction reminders | Keep upgrade visible |
| 6. Re-engagement | 3rd app open as free | Dismissible top banner | One last gentle nudge |
| 7. Post-purchase | StoreKit/Razorpay success | Confetti → return to action that triggered paywall | Close the loop |
| 8. Plus-user lifecycle | Renewal failed → `past_due` → 3 days → `expired` | In-app banner: "Payment failed — update method" | Reduce involuntary churn |

**Plus user "feels Plus" mechanic**: after upgrade, the gradient crest replaces the avatar border on the profile tab icon for 7 days (subtle, persistent reward). The brainstorm counter pill shows `∞` instead of a number. Concierge tab gets a small "Plus" gradient dot on first launch post-upgrade.

**Dunning copy** (`past_due` state):
- iOS: a yellow banner on the trip list — "We couldn't renew your Plus subscription. Update payment method →" (deep-links to Apple subscription management).
- Web: same banner above the profile nav rail; CTA opens Razorpay update-payment flow.

### 9. Cross-Platform Consistency

- **Single source of truth = backend `User.subscription_tier`**. Clients never trust local state.
- iOS purchases push to `/billing/apple/verify`; Razorpay pushes via webhook. Both write to the same User row.
- A user who subscribes via web sees Plus on iOS automatically (and vice versa for restore-purchases on the same Apple ID linked to same email).

---

## Critical Files to Modify

**Backend:**
- `backend/app/models/all_models.py` — add fields + `SubscriptionEvent`, `UsageCounter`
- `backend/app/services/entitlements.py` — **new**
- `backend/app/services/payments/razorpay_service.py` — **new**
- `backend/app/services/payments/apple_service.py` — **new**
- `backend/app/api/endpoints/billing.py` — **new**
- `backend/app/api/endpoints/brainstorm.py:123` — wrap with `enforce_or_raise` + counter bump
- `backend/app/api/endpoints/concierge.py:173` — wrap with `enforce_or_raise`
- `backend/app/api/endpoints/trips.py:36-62` — active-trip gate on create
- `backend/app/core/config.py` — Razorpay + Apple env keys
- `backend/alembic/versions/` — new migration

**Web (Next.js):**
- `frontend/app/pricing/page.tsx` — **new** public pricing page
- `frontend/app/profile/subscription/page.tsx` — replace stub with free/Plus states
- `frontend/app/profile/layout.tsx:12` — Upgrade pill (free) / Plus gradient pill (Plus)
- `frontend/components/PaywallModal.tsx` — **new** contextual modal
- `frontend/components/PlusCrest.tsx` — **new** reusable gradient crest with shimmer keyframe
- `frontend/components/TierComparison.tsx` — **new** shared between subscription page, paywall, pricing
- `frontend/components/OnboardingPlusStep.tsx` — **new** onboarding Step B
- `frontend/hooks/useEntitlement.ts` — **new** entitlement hook + PaywallProvider context
- `frontend/components/PlusUpgradeBanner.tsx` — **new** re-engagement & dunning banners
- `frontend/components/BrainstormQuotaPill.tsx` — **new** inline counter pill
- Update `frontend/app/trips/[id]/page.tsx` — concierge tab locked state, brainstorm pane quota pill, offline map toggle
- `frontend/app/onboarding/*` — extend post-persona flow with Screens A & B
- Razorpay Checkout `<script>` include in root layout
- `frontend/app/globals.css` — add `@keyframes pulse-soft` and `@keyframes plus-shimmer`

**iOS:**
- `ios/Roammate/Subscription/StoreKitClient.swift` — **new**
- `ios/Roammate/Subscription/SubscriptionStore.swift` — **new**
- `ios/Roammate/Views/Profile/SubscriptionView.swift` — replace stub (free + Plus states)
- `ios/Roammate/Views/Profile/ProfileTabView.swift` — Subscription row: gradient icon + Upgrade/Plus trailing label
- `ios/Roammate/Views/Paywall/PaywallSheet.swift` — **new** contextual sheet
- `ios/Roammate/Views/Paywall/PlusCrestView.swift` — **new** animated gradient crest
- `ios/Roammate/Views/Paywall/TierComparisonList.swift` — **new** reusable
- `ios/Roammate/Views/Paywall/ConfettiBurst.swift` — **new** Canvas-based confetti
- `ios/Roammate/Views/Onboarding/PlusOnboardingScreens.swift` — **new** Screens A & B
- `ios/Roammate/Views/Common/QuotaPill.swift` — **new** brainstorm counter pill
- `ios/Roammate/Views/Common/PaywallObserverModifier.swift` — **new** root paywall observer
- `ios/Roammate/Network/APIClient.swift:164` — extend `APIError.paymentRequired(feature:)`
- `ios/Roammate/Store/AuthManager.swift` — boot SubscriptionStore
- `ios/Roammate/Views/Trips/Brainstorm/BrainstormPaneView.swift` — quota pill
- `ios/Roammate/Views/Trips/SubPages/TripConciergeView.swift` — locked state for free
- `ios/Roammate/Views/Trips/CreateTripView.swift` — pre-emptive paywall on active-trip cap
- `ios/Roammate/Views/Trips/Plan/PlanMapPage.swift` — offline toggle paywall popover
- `ios/Roammate/Theme/RoammateTheme.swift` — add `RoammateGradient.plus` (indigo→fuchsia→amber) constant
- `ios/Roammate.xcodeproj` — IAP capability + `.entitlements` file

---

## Reused Existing Code

- `User`, `Trip`, `TripMember` models (`all_models.py:32-112`) — no auth or trip-ownership work needed.
- `TokenUsage` table (`all_models.py:229-243`) — already logs LLM cost per user; reuse for unit-economics dashboards.
- `get_current_user` dep (`api/deps.py:13-36`) — all gated endpoints already inject the user.
- iOS `KeychainHelper`, `AuthManager`, `APIClient` Bearer-token plumbing — IAP receipt-verify request reuses it as-is.
- Next.js `useAuth` — extend rather than replace.
- Existing concierge "coming soon" `TripConciergeView.swift:9-13` and `profile/subscription/page.tsx:10-16` stubs — replace in place.

---

## Sequencing (build order)

1. **Backend foundation** — User fields, migration, `entitlements.py`, gate the 3 endpoints with stub "always free". Verify 402s by hand via curl.
2. **Razorpay end-to-end on web** — billing endpoints, webhook (test in Razorpay test mode), pricing page, paywall modal, profile/subscription page.
3. **Apple IAP on iOS** — App Store Connect config, StoreKit 2 client, verify endpoint, SubscriptionStore, SubscriptionView, paywall sheet on 402.
4. **Polish** — usage counter UI ("12 / 15 brainstorms used this month"), email receipts, dunning copy for `past_due`.

---

## Verification

- **Backend unit/integration tests** (`backend/tests/`):
  - Free user with 2 active trips → `POST /trips` with future end_date returns 402.
  - Free user, 16th brainstorm of month → 402.
  - Free user, any concierge POST → 402.
  - Plus user → all pass.
  - Webhook: simulate Razorpay `subscription.activated` payload → user flips to plus.
  - Webhook: simulate Razorpay `subscription.halted` → user flips back to free, active trips read-only.
- **Razorpay test mode** end-to-end: create test subscription, complete UPI/card auth, observe webhook, verify `User.subscription_tier=plus`. Use Razorpay test cards & test UPI VPA.
- **Apple sandbox**: create sandbox tester, run iOS app, purchase `com.roammate.app.plus.monthly`, verify `/billing/apple/verify` sets tier=plus. Test renewal acceleration, cancellation, refund via App Store Connect.
- **Cross-platform**: subscribe on web, open iOS → entitlement reflects Plus.
- **Manual UX QA** in dev server (`docker compose up`, Next.js dev, Xcode sim): walk through soft-paywall flow described in §8.
- **Regression**: existing brainstorm and concierge flows for a Plus user behave identically to today (no model swap, no latency).

---

## Out of Scope (deferred)

- Annual plan + discount (v2).
- Stripe / international currencies (v2).
- Promo codes & coupons.
- Premium LLM model tier for Plus.
