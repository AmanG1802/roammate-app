# Paywall Triggers — Web vs iOS

Inventory of every place the Roammate Plus paywall can open, on each platform, and how the two implementations differ architecturally.

## Architecture difference (the big one)

|  | Web | iOS |
|---|---|---|
| **How the paywall opens** | Each call site must explicitly call `requirePlus(feature)` from `useEntitlement()` | `APIClient.swift:217-223` auto-posts `.needsPlus` on **every 402** with a `needs_plus` payload; `PaywallObserverModifier` listens app-wide |
| **Mounted listener?** | No global listener — `PaywallModal` only opens via `pendingPaywall` state set by `requirePlus()` | `PaywallObserverModifier` (`Views/Paywall/PaywallObserver.swift`) mounted once on root |
| **402 fallback** | Each fetch must use `isNeedsPlus(body)` + call `requirePlus()` manually | Free — APIClient does it; UI just gets a thrown `paymentRequired` |

iOS gets implicit paywall coverage for any 402-returning endpoint. On web, each new endpoint has to opt in at the call site — a new `needs_plus`-returning endpoint will silently fail unless the caller wires up `isNeedsPlus(body)`.

## Web — `requirePlus(...)` call sites

| Location | Feature | Why it fires |
|---|---|---|
| `frontend/app/dashboard/page.tsx:278` | `active_trips` (or server-sent) | Create-trip API returned 402 |
| `frontend/components/dashboard/DashboardTripPlanner.tsx:87` | `brainstorm_quota` | Inline brainstorm API returned 402 |
| `frontend/components/trip/BrainstormChat.tsx:87` | `brainstorm_quota` | Brainstorm send returned 402 |
| `frontend/components/trip/BrainstormChat.tsx:300` | `brainstorm_quota` | User clicks the inline "out of brainstorms" CTA |
| `frontend/components/billing/QuotaPill.tsx:35` | `brainstorm_quota` | User clicks quota pill while `remaining === 0` |
| `frontend/components/trip/ConciergeActionBar.tsx:37` | `concierge` | Free user taps Concierge action |
| `frontend/components/billing/PlusBanner.tsx:101` | `concierge` | Past-due / re-engagement / generic banner CTA |
| `frontend/components/billing/PlusBanner.tsx:183` | `concierge` | One-time-expiry banner CTA |
| `frontend/components/billing/OnboardingPlusModal.tsx:39` | `concierge` | "See Plus" inside the post-persona onboarding modal |
| `frontend/app/profile/subscription/page.tsx:137` | `concierge` (plan: monthly) | Subscription page "Go monthly" CTA |
| `frontend/app/profile/subscription/page.tsx:153` | `concierge` (plan: one_time) | Subscription page "One-time" CTA |
| `frontend/app/profile/subscription/page.tsx:345` | `concierge` | Plus user "manage / re-pitch" CTA |
| `frontend/app/pricing/page.tsx:35` | `concierge` | Marketing pricing page CTA (signed-in only) |

## iOS — `.needsPlus` posts + direct `PaywallSheet` mounts

| Location | Feature | Why it fires |
|---|---|---|
| `ios/Roammate/Network/APIClient.swift:219` | server-sent | **Auto-trigger on any 402 with `needs_plus`** — implicit, covers create-trip, brainstorm send, concierge, etc. |
| `ios/Roammate/Views/Onboarding/PlusOnboardingSheet.swift` (via `MainShell.swift:83`) | `concierge` | "See Plus" inside the post-onboarding sheet |
| `ios/Roammate/Views/Trips/Brainstorm/BrainstormChatView.swift:13` | `brainstorm_quota` | User taps the brainstorm pill while `remaining == 0` |
| `ios/Roammate/Views/Trips/Brainstorm/BrainstormChatView.swift:272` | `brainstorm_quota` | User taps Send while quota exhausted (pre-empts the 402) |
| `ios/Roammate/Views/Paywall/PlusBanners.swift:66` | `concierge` | One-time-expiry banner CTA |
| `ios/Roammate/Views/Paywall/PlusBanners.swift:131` | `concierge` | General Plus upsell banner CTA |
| `ios/Roammate/Views/Profile/SubscriptionView.swift:329` | `concierge` | "Switch to monthly" from one-time |
| `ios/Roammate/Views/Profile/SubscriptionView.swift:41` | `concierge` | Direct `PaywallSheet` mount (not via notification) for the Subscription view's own paywall flow |

## Parity gaps worth knowing

1. **iOS has no separate Pricing page paywall entry** (no equivalent of `app/pricing/page.tsx`) — `SubscriptionView` is the only standalone surface.
2. **iOS has no equivalent of `ConciergeActionBar` / `QuotaPill` standalone components** — the concierge entry point is via banners and the 402 auto-trigger; the quota pill exists but is local to `BrainstormChatView`.
3. **Web has no auto-trigger** — any backend endpoint that returns `needs_plus` without a matching `isNeedsPlus()` check at the call site silently fails. File this when adding a new 402 endpoint on web.
4. **Web has more "manual" upsell CTAs** in the Subscription/Pricing pages (monthly vs one-time as separate CTAs); iOS funnels both through one `PaywallSheet` with a `preferredPlan` parameter.
5. **Plan preselection transport**: web uses `requirePlus('concierge', { plan: 'monthly' | 'one_time' })`; iOS uses `userInfo["preferredPlan"]` on the notification — same intent, different transport.

## Coupon codes

Coupons are stored in the `coupon` table — these are the rows seeded at launch (`backend/migrations/003_coupons_and_onetime.sql:50-61`). To add or change one, write a new migration; nothing is hardcoded in app code.

| Code | Applies to | Discount | Final price | Validity (from seed) | Per-user redemptions | Notes |
|---|---|---|---|---|---|---|
| `EARLYACCESS` | `one_time` (₹200 / 30-day plan) | `flat_off` of 20000 paise (₹200) | **₹0** — backend grants Plus directly, no payment processor touched | 90 days from seed | 1 | Positioned as an internal "invitation code" for early-access users. On iOS, free-grant short-circuits StoreKit (Apple won't process ₹0). See `docs/[23] subscription-coupons-onetime.md` for the App Store review stance. |
| `EARLYSALE` | `subscription_first_cycle` (monthly ₹149) | `fixed_price` of 4900 paise (₹49) — first cycle only | **₹49 first month, then ₹149/mo** | 60 days from seed | 1 | Delivered via **Razorpay Offer** on web and **Apple Promotional Offer** (signed JWS) on iOS — the payment provider does the discount math. Operator must also create the matching Razorpay Offer (`backend/scripts/sync_coupon_to_razorpay.py`) and the App Store Connect promo offer; `razorpay_offer_id` / `apple_offer_id` get stamped on the coupon row. |

### How coupons are validated

`backend/app/services/coupons.py:119-165` (`validate_and_quote`) checks, in order:

1. Code exists (`coupon_not_found`)
2. `is_active` (`coupon_inactive`)
3. `valid_from` / `valid_until` window (`coupon_not_yet_active` / `coupon_expired`)
4. `applies_to` matches the requested target — `one_time` or `subscription` (`coupon_wrong_target`)
5. Not already redeemed by this user (`coupon_already_redeemed`) — enforced via `UNIQUE(coupon_id, user_id)` on `coupon_redemption`

### Where coupon codes are entered in the UI

- **Web**: `PaywallModal.tsx` has a coupon input on both the monthly and one-time tabs. EARLYACCESS on one-time → backend free-grant path, no Razorpay round-trip.
- **iOS**: `Views/Paywall/CouponInputView.swift` (used inside `PaywallSheet`). EARLYSALE flows through `SubscriptionStore.purchaseMonthly(couponCode:)` which calls `/billing/apple/redeem-offer` for a signed offer before StoreKit. EARLYACCESS on one-time short-circuits to `/billing/razorpay/one-time` free-grant.

## Feature codes

Backend can emit any of these in the `needs_plus` 402 payload; both clients route them to the appropriate copy:

- `concierge`
- `brainstorm_quota`
- `active_trips`
- `offline_maps`
