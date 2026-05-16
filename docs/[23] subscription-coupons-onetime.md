# Extension v1.1 — Promo Codes & One-Time Payment

## Context (v1.1)

The v1 launch (above) ships only the ₹149/mo subscription with no discounts. To accelerate launch conversion and capture users who resist auto-renewing commitments, v1.1 adds:

1. A **₹200 one-time payment** plan that grants Plus for exactly 30 days with no auto-renewal. Targets users who want to "try Plus" without subscribing, or who have UPI mandate aversion.
2. A **coupon code system** with two launch codes:
   - **EARLYACCESS** — `₹200 off` the one-time plan → free 30-day Plus grant. Internal launch reward.
   - **EARLYSALE** — first month of the monthly subscription at `₹49`, then `₹149/mo` thereafter. Acquisition lever.

Both are **per-user single-use** and **time-bounded** (start/end dates). No global redemption caps in v1.1 (add later if abused). No stacking — at most one code per checkout.

## Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| One-time plan expiry behavior | Hard-expire to free + nudge banner days 25–30 | Matches "one-time" framing; banner targets conversion to monthly |
| Coupon limits | Per-user single-use + time-bounded validity windows | Prevents farming; lets us run dated promos |
| iOS one-time availability | Yes — separate StoreKit product (`com.roammate.app.plus.onetime`, **non-renewing subscription** type) | Apple rules require IAP for in-app digital unlocks; non-renewing-sub product type is purpose-built for 30-day grants |
| Coupon management | Hybrid — custom backend `coupons` table for one-time + Razorpay Offers API for monthly first-cycle discounts | Backend owns one-time math; Razorpay Offers natively handle subscription billing-cycle discounts |
| EARLYACCESS discount | `₹200 off` on one-time → final `₹0` (free grant, no payment processor touched) | Skip Razorpay/Apple; backend grants tier directly with redemption record |
| iOS EARLYSALE delivery | **Apple Promotional Offer** (code-gated, signed JWS) | Parity with web — only code-bearing users get the discount, matches Razorpay Offers behavior |
| Coupon entry UX | Hidden behind "Have a code?" link; also auto-apply via `?promo=CODE` URL param | Industry standard; clean default UI; supports email/marketing funnels |

## Tier Matrix Update

| Plan | Price | Duration | Auto-renew | Coupons | Tier on expiry |
|---|---|---|---|---|---|
| Free | ₹0 | n/a | n/a | n/a | n/a |
| Plus — One-time | **₹200** | 30 days | **No** | EARLYACCESS (`-₹200`) | Free (hard) |
| Plus — Monthly | **₹149/mo** | Recurring | Yes | EARLYSALE (first-month `₹49`) | Free on cancel/halt |

---

## A. Data Model Changes

**New table `Coupon`** (`backend/app/models/all_models.py`):

```python
class Coupon(Base):
    id: int (PK)
    code: str  unique  index  # uppercase, e.g. "EARLYACCESS"
    description: str | None
    discount_type: str  # "flat_off" | "percent_off" | "fixed_price"
    discount_value: int  # paise for flat_off / fixed_price; basis-points for percent_off (e.g., 5000 = 50%)
    applies_to: str  # "one_time" | "subscription_first_cycle" | "any"
    valid_from: datetime
    valid_until: datetime
    max_redemptions_per_user: int = 1
    razorpay_offer_id: str | None  # only set for subscription codes; mirrors Razorpay Offer
    apple_offer_id: str | None  # only set for subscription codes; matches App Store Connect promo offer
    is_active: bool = True
    created_at, updated_at
```

**New table `CouponRedemption`**:

```python
class CouponRedemption(Base):
    id: int (PK)
    coupon_id: int  FK->Coupon
    user_id: int  FK->User  index
    provider: str  # "razorpay" | "apple" | "internal_grant"
    payment_external_id: str | None  # razorpay payment_id, apple transaction_id, or null for free grants
    amount_paid_paise: int  # 0 for full-discount, else discounted total
    applied_at_period_start: datetime
    created_at: datetime
    __table_args__ = (UniqueConstraint("coupon_id", "user_id"),)
```

**`User` table additions** (small, for one-time tracking):

```python
last_one_time_purchase_at: datetime | None  # when most recent ₹200 plan was activated
last_one_time_external_id: str | None  # razorpay payment_id or apple original_transaction_id
```

Add to `subscription_status` allowed values: `"one_time"` (active one-time grant with hard expiry).

**Migration**: New raw-SQL file `backend/migrations/003_coupons_and_onetime.sql` (auto-migrate handles table creation but not the string `server_default` if needed for status enum widening — apply same way as `002`).

**Seed data**: SQL inserts for the two launch coupons (run once on prod after migration):

```sql
INSERT INTO coupons (code, discount_type, discount_value, applies_to, valid_from, valid_until, max_redemptions_per_user, is_active)
VALUES
  ('EARLYACCESS', 'flat_off', 20000, 'one_time', NOW(), NOW() + INTERVAL '90 days', 1, true),
  ('EARLYSALE',   'fixed_price', 4900, 'subscription_first_cycle', NOW(), NOW() + INTERVAL '60 days', 1, true);
```

For EARLYSALE, after creating the row, the operator runs a one-off script (`backend/scripts/sync_coupon_to_razorpay.py`) that:
1. Creates a Razorpay Offer via Offers API (`payment_method=upi,card`, `redemption_type=once_per_subscription`, `display_name="EARLYSALE - First month ₹49"`) and stores the returned `offer_id` on the row.
2. Notes the Apple Promotional Offer ID (manually configured in App Store Connect with offer code `EARLYSALE`) on the row.

---

## B. Backend Services

### B.1 Coupon Service (new — `backend/app/services/coupons.py`)

```python
@dataclass
class CouponQuote:
    coupon_id: int
    code: str
    applies_to: str
    original_amount_paise: int
    discount_amount_paise: int
    final_amount_paise: int
    razorpay_offer_id: str | None
    apple_offer_id: str | None

async def validate_and_quote(
    db, user, code: str, target: Literal["one_time", "subscription"]
) -> CouponQuote:
    """
    Raises HTTPException(400) with detail.code in:
      - "coupon_not_found" | "coupon_expired" | "coupon_inactive"
      - "coupon_already_redeemed"
      - "coupon_wrong_target"
    Returns CouponQuote with final_amount_paise (may be 0).
    """

async def record_redemption(
    db, user, coupon, provider, payment_external_id, amount_paid_paise
) -> CouponRedemption:
    """Inserts CouponRedemption row inside the same txn that flips user tier.
    Idempotent via the (coupon_id, user_id) unique constraint — on conflict, return existing row."""
```

The `validate_and_quote` function is read-only — it doesn't reserve the coupon. Reservation happens at `record_redemption` time, which is called from within the webhook/verify handlers under a single transaction.

### B.2 Razorpay Service additions (`backend/app/services/payments/razorpay_service.py`)

```python
def create_one_time_order(amount_paise: int, notes: dict) -> dict:
    """Creates a Razorpay Order (not subscription). Returns {order_id, amount, currency, key_id}.
    Used for ₹200 one-time plan. If coupon brings amount to 0, we skip Razorpay entirely (handled at endpoint level)."""

def create_monthly_subscription(
    email, name, total_count=120, notes, offer_id: str | None = None
) -> dict:
    """ADD offer_id arg. When set, passes through to subscription.create() so the first cycle uses
    the Razorpay Offer discount. Idempotent — second create with same notes.coupon_redemption_id returns existing."""

def verify_order_signature(order_id, payment_id, signature) -> bool:
    """For one-time orders: Razorpay Checkout returns (payment_id, order_id, signature).
    Verify HMAC(order_id|payment_id) == signature with key_secret. Required before granting access."""
```

### B.3 Apple Service additions (`backend/app/services/payments/apple_service.py`)

```python
def is_one_time_product(product_id: str) -> bool:
    return product_id == settings.APPLE_IAP_PRODUCT_ID_ONETIME  # com.roammate.app.plus.onetime

def sign_promotional_offer(
    product_id: str, offer_id: str, username_hash: str, nonce: str, timestamp: int
) -> str:
    """Signs Apple Promotional Offer with ES256 using APPLE_PROMO_OFFER_P8_KEY.
    Returns the signature string passed to StoreKit Product.PurchaseOption.promotionalOffer(...).
    Per Apple docs: payload = bundleId\nappBundleVersion\nkeyId\nproductId\nofferId\nusernameHash\nnonce\ntimestamp
    """
```

Required new env vars in `config.py`:

```python
APPLE_IAP_PRODUCT_ID_ONETIME = "com.roammate.app.plus.onetime"
APPLE_PROMO_OFFER_KEY_ID: str  # from App Store Connect, dedicated subscription-offer key
APPLE_PROMO_OFFER_P8_KEY: str  # PEM-encoded ES256 private key (single-line, \n-escaped)
RAZORPAY_OFFER_ID_EARLYSALE: str | None  # populated via sync script, also stored on coupon row
PLUS_ONETIME_PRICE_INR: int = 200
PLUS_ONETIME_DURATION_DAYS: int = 30
```

### B.4 Endpoint additions (`backend/app/api/endpoints/billing.py`)

**POST `/billing/coupons/validate`**

Request: `{ "code": "EARLYACCESS", "target": "one_time" }`
Response (success):
```json
{
  "code": "EARLYACCESS",
  "original_amount_paise": 20000,
  "discount_amount_paise": 20000,
  "final_amount_paise": 0,
  "applies_to": "one_time",
  "display_message": "₹200 off — your first 30 days are on us"
}
```
Response (error): `400` with `{detail: {code, message}}`.

Note: this endpoint does NOT redeem. It's a UX preview. Redemption happens at checkout completion.

**POST `/billing/razorpay/one-time`**

Request: `{ "coupon_code": "EARLYACCESS" | null }`

Logic:
- Compute `final_amount_paise` (₹200 or ₹0 if EARLYACCESS valid).
- **If `final_amount_paise == 0`**: bypass Razorpay entirely. In a single DB transaction:
  - Set `user.subscription_tier="plus"`, `subscription_status="one_time"`, `subscription_provider="internal_grant"`, `subscription_current_period_end = now + 30 days`, `last_one_time_purchase_at = now`.
  - Insert `CouponRedemption(provider="internal_grant", payment_external_id=None, amount_paid_paise=0)`.
  - Return `{ "granted": true, "period_end": ... }`. Client polls `/billing/status` and shows confetti.
- **Else**: create Razorpay Order with `amount_paise=final_amount_paise`, `notes={user_id, coupon_id|null, type:"one_time"}`. Return `{order_id, amount_paise, key_id, coupon_id}` to client. Client opens Razorpay Checkout in "Order" mode.

**POST `/billing/razorpay/one-time/verify`**

Called by client after Razorpay Checkout success. Request: `{order_id, payment_id, signature, coupon_id?}`.
- Verify signature.
- Fetch payment to confirm `captured` status and amount.
- Single DB txn: set tier/status/period_end (status `"one_time"`, period_end `+30 days`), insert `CouponRedemption` if coupon_id present, insert `SubscriptionEvent(provider="razorpay", event_type="one_time.captured", event_id=payment_id)` for idempotency.

**POST `/billing/razorpay/subscription`** — **MODIFY**

Add `coupon_code` to request body. If present:
- Validate via `validate_and_quote(target="subscription")`.
- Look up `coupon.razorpay_offer_id`; pass `offer_id` to `create_monthly_subscription`.
- Stash `coupon_id` in subscription `notes` for webhook redemption recording.

The Razorpay webhook (`subscription.charged` event) already exists; ADD logic: if event payload's subscription has `notes.coupon_id`, call `record_redemption` on first charge. Subsequent charges no-op (unique constraint).

**POST `/billing/apple/redeem-offer`** (new)

Used by iOS to fetch a signed Apple Promotional Offer payload before calling StoreKit `purchase(options:)`. Request: `{ "code": "EARLYSALE" }`. Response:
```json
{
  "product_id": "com.roammate.app.plus.monthly",
  "offer_id": "earlysale_first_month_49",
  "key_id": "ABC123",
  "nonce": "uuid-v4",
  "timestamp": 1747400000000,
  "signature": "base64-ES256-sig",
  "coupon_id": 42
}
```

iOS passes these into `Product.PurchaseOption.promotionalOffer(...)`. On successful StoreKit transaction, iOS calls `/billing/apple/verify` with `coupon_id` in the request body. Backend records redemption in same txn as tier flip.

**POST `/billing/apple/verify`** — **MODIFY**

Accept optional `coupon_id` in request. Also detect product_id: if it matches `APPLE_IAP_PRODUCT_ID_ONETIME`, set `subscription_status="one_time"` and `subscription_current_period_end = now + 30 days` (NOT the JWS `expires_date`, which doesn't exist for non-renewing subs). Otherwise the existing monthly subscription path.

**POST `/billing/apple/webhook`** — **MODIFY**

Non-renewing subscriptions don't send renewal notifications. They DO send `REFUND` and `REVOKE` events — handle those by flipping user to `free` if the refunded transaction matches `last_one_time_external_id`.

---

## C. Frontend (Web)

### C.1 Paywall modal coupon UX (`frontend/components/billing/PaywallModal.tsx`)

Add below the price line, above the CTAs:

```
Plan toggle: [ Monthly ₹149 ]  [ One-time ₹200 / 30 days ]   <- pill switcher
[ Have a code? ▼ ]
  ┌─────────────────────────────────┐
  │ Enter code              [APPLY] │   <- input + button row, slides down 180ms
  └─────────────────────────────────┘
  ✓ EARLYACCESS applied — ₹200 off    <- success state, emerald
  ✗ This code can't be used here       <- error state, rose
```

Behaviors:
- Switching to "One-time" updates the CTA copy to "Pay ₹200" and changes the post-success messaging.
- "Have a code?" expands the input with Framer Motion height animation.
- On Apply, call `POST /billing/coupons/validate` with the current selected plan as `target`. Show the `display_message` on success, clear and re-quote on plan switch.
- The CTA button label dynamically reflects the quoted final amount: "Pay ₹0 (claim free month)" when EARLYACCESS lands the one-time plan at 0.
- Auto-apply: on mount, read `?promo=` from `window.location.search`; if present, pre-fill the field, auto-expand the section, and auto-trigger Apply.

On subscribe:
- Monthly: existing flow + pass `coupon_code` to `POST /billing/razorpay/subscription`.
- One-time + final_amount_paise=0: call `POST /billing/razorpay/one-time` — server grants immediately, modal jumps to confetti success state.
- One-time + final_amount_paise>0: call `POST /billing/razorpay/one-time` to create order, then open Razorpay Checkout in `order_id` mode (not `subscription_id`), on success call `/billing/razorpay/one-time/verify`.

### C.2 Pricing page (`frontend/app/pricing/page.tsx`)

Add a third visual card: "One-time" between Free and Monthly. Hero shows both prices side-by-side with the "Or pay ₹200 once for 30 days" subtitle.

### C.3 Subscription management page (`frontend/app/profile/subscription/page.tsx`)

When `entitlement.status === "one_time"`:
- Status banner: "You're on Plus (one-time, 30 days)" with `period_end` countdown.
- Replace cancel button with: "Switch to monthly subscription" CTA (opens paywall in monthly mode).
- Show a thin amber banner during days 25–30: "Your Plus access ends in N days — keep going for ₹149/mo".

### C.4 Entitlement hook (`frontend/hooks/useEntitlement.tsx`)

No interface changes — `status` already typed as `string`. Just consume the new `"one_time"` literal in UI branches.

### C.5 New component `frontend/components/billing/CouponInput.tsx`

Self-contained controlled component for the code input + apply button + state messages. Reused by PaywallModal and subscription page.

---

## D. Frontend (iOS)

### D.1 StoreKit additions (`ios/Roammate/Subscription/StoreKitClient.swift`)

Add second product ID to load: `com.roammate.app.plus.onetime`. Treat as non-renewing subscription:

```swift
let productIds = [
    "com.roammate.app.plus.monthly",
    "com.roammate.app.plus.onetime",
]
```

New method:
```swift
func purchaseOneTime() async throws -> VerificationResult<Transaction>?
func purchaseMonthly(withPromotionalOffer offer: SignedPromotionalOffer?) async throws -> ...
```

`SignedPromotionalOffer` is a new struct that holds the response from `/billing/apple/redeem-offer`. Convert to `Product.PurchaseOption.promotionalOffer(offerID:, keyID:, nonce:, signature:, timestamp:)`.

### D.2 SubscriptionStore (`ios/Roammate/Subscription/SubscriptionStore.swift`)

Add:
```swift
func validateCoupon(_ code: String, target: CouponTarget) async throws -> CouponQuote
func purchaseOneTime(couponCode: String?) async throws
func purchaseMonthly(couponCode: String?) async throws  // replaces existing purchase()
```

For zero-amount EARLYACCESS on one-time: skip StoreKit entirely (Apple won't let you charge ₹0). Backend `/billing/razorpay/one-time` (renamed to `/billing/grant/one-time` may be cleaner) returns `granted: true` — store calls `refresh()`.

**Important**: Apple's IAP rules technically REQUIRE all in-app digital unlocks to use IAP. A backend-granted free unlock for a coupon code earned outside the App Store is a grey area. Mitigation: the EARLYACCESS coupon is positioned as an "invitation code" (one we hand-distribute to internal/beta users), not a publicly advertised discount. App Store review tolerates this pattern (e.g., Notion, Linear). Document this stance in App Store Connect's review notes.

For non-zero monthly with EARLYSALE: call `/billing/apple/redeem-offer` to get signed offer → pass to StoreKit `purchaseMonthly`. Apple charges first cycle at the offer price, subsequent cycles at base price.

### D.3 Paywall sheet (`ios/Roammate/Views/Paywall/PaywallSheet.swift`)

Add segmented control above the price block:

```
┌──────────────────────────────────┐
│  [ Monthly ]  [ One-time ]       │  <- Picker.segmented
└──────────────────────────────────┘
```

Below price, a `DisclosureGroup("Have a code?")` reveals a `TextField` (auto-capitalized, `.allCharacters`) and an Apply button. On Apply, calls `store.validateCoupon(...)` and displays the resulting quote inline.

CTA label binds to the quoted price.

Plan toggle changes the bound CTA action: `store.purchaseMonthly` vs `store.purchaseOneTime`.

### D.4 SubscriptionView (`ios/Roammate/Views/Profile/SubscriptionView.swift`)

Mirror web's `"one_time"` state: countdown badge, "Switch to monthly" CTA, amber expiry banner in days 25–30 (computed from `period_end - now`).

### D.5 Paywall observer (`PaywallObserver.swift`)

No changes — same feature-keyed sheet, just richer body.

---

## E. Critical Files to Modify (v1.1)

**Backend:**
- `backend/app/models/all_models.py` — add `Coupon`, `CouponRedemption`, two User columns
- `backend/migrations/003_coupons_and_onetime.sql` — **new**
- `backend/scripts/sync_coupon_to_razorpay.py` — **new** one-shot helper
- `backend/scripts/seed_launch_coupons.py` — **new** seeds EARLYACCESS + EARLYSALE
- `backend/app/services/coupons.py` — **new**
- `backend/app/services/payments/razorpay_service.py` — add `create_one_time_order`, `verify_order_signature`, extend `create_monthly_subscription` with `offer_id`
- `backend/app/services/payments/apple_service.py` — add `is_one_time_product`, `sign_promotional_offer`
- `backend/app/api/endpoints/billing.py` — 4 new endpoints (`/coupons/validate`, `/razorpay/one-time`, `/razorpay/one-time/verify`, `/apple/redeem-offer`), 2 modified (`/razorpay/subscription`, `/apple/verify`)
- `backend/app/core/config.py` — env vars listed in §B.3

**Web:**
- `frontend/components/billing/CouponInput.tsx` — **new**
- `frontend/components/billing/PaywallModal.tsx` — plan toggle, coupon section, branching subscribe paths, auto-apply from `?promo=`
- `frontend/components/billing/PlanToggle.tsx` — **new** Monthly/One-time segmented control
- `frontend/app/pricing/page.tsx` — add one-time card, "Or pay ₹200 once" subtitle
- `frontend/app/profile/subscription/page.tsx` — render `"one_time"` status branch
- `frontend/components/billing/PlusBanner.tsx` — new `OneTimeExpiryBanner` (days 25–30)
- `frontend/app/dashboard/page.tsx` — mount `<OneTimeExpiryBanner />`

**iOS:**
- `ios/Roammate/Subscription/StoreKitClient.swift` — load both products; `purchaseOneTime`; `purchaseMonthly(withPromotionalOffer:)`
- `ios/Roammate/Subscription/SubscriptionStore.swift` — `validateCoupon`, `purchaseOneTime`, refactor `purchase` → `purchaseMonthly`
- `ios/Roammate/Subscription/Entitlement.swift` — add `couponQuote` codable
- `ios/Roammate/Subscription/RoammatePlus.storekit` — add second product entry (non-renewing sub, ₹200, 30d)
- `ios/Roammate/Views/Paywall/PaywallSheet.swift` — plan picker + coupon disclosure
- `ios/Roammate/Views/Paywall/CouponInputView.swift` — **new**
- `ios/Roammate/Views/Profile/SubscriptionView.swift` — one-time state UI
- `ios/Roammate/Views/Paywall/PlusBanners.swift` — `OneTimeExpiryBanner`
- `ios/Roammate/Views/Dashboard/DashboardView.swift` — mount the new banner
- `ios/Roammate.xcodeproj/project.pbxproj` — register new Swift files via xcodeproj script

**App Store Connect / Razorpay Dashboard (manual):**
- App Store Connect → in-app purchases → create `com.roammate.app.plus.onetime` (non-renewing subscription, ₹200 tier)
- App Store Connect → subscription group `roammate_plus` → add **Promotional Offer** named `earlysale_first_month_49` (1 period at ₹49, code-gated)
- App Store Connect → keys → create a **Subscription Offers** key, download `.p8`, store in env (`APPLE_PROMO_OFFER_KEY_ID`, `APPLE_PROMO_OFFER_P8_KEY`)
- Razorpay dashboard → Offers → create `EARLYSALE_FIRST_MONTH_49` offer (`flat_off ₹100`, applicable to monthly plan, once per subscription, valid 60 days), copy `offer_id` into `RAZORPAY_OFFER_ID_EARLYSALE` env + the `coupons.razorpay_offer_id` row

---

## F. Verification (v1.1)

**Backend integration tests** (`backend/tests/test_coupons.py`):
- Validate EARLYACCESS with `target=one_time` → `final_amount_paise=0`.
- Validate EARLYACCESS with `target=subscription` → 400 `coupon_wrong_target`.
- Validate EARLYACCESS twice for same user → second call 400 `coupon_already_redeemed` (after first redemption recorded).
- Validate code outside `valid_from..valid_until` → 400 `coupon_expired`.
- `POST /billing/razorpay/one-time` with EARLYACCESS → returns `granted: true`, user flips to `tier=plus, status=one_time, period_end≈now+30d`.
- Without coupon, `POST /billing/razorpay/one-time` → returns order_id, user state unchanged until verify.
- `POST /billing/razorpay/one-time/verify` with bogus signature → 400.
- `POST /billing/apple/verify` with one-time product JWS → `status=one_time`, `period_end=now+30d`.
- Apple `REFUND` webhook for one-time transaction → user back to free.

**Razorpay test mode end-to-end:**
- Create test order via `/billing/razorpay/one-time`, complete with test card, verify webhook + tier flip + redemption row.
- Create subscription with `coupon_code=EARLYSALE`, observe first invoice at ₹49 then renewal at ₹149.

**Apple sandbox end-to-end:**
- Configure sandbox tester, purchase one-time product, verify backend flip.
- Redeem `EARLYSALE` offer code in iOS app: `/billing/apple/redeem-offer` → signed payload → `purchase(options:)` → first cycle at ₹49.
- Verify next renewal in accelerated sandbox time charges ₹149.

**Manual UX QA:**
- Auto-apply `?promo=EARLYACCESS` on `/pricing` lands a 0-charge claim flow.
- "Have a code?" disclosure animates open/close on both platforms.
- Days 25–30 expiry banner appears on dashboard for users with `status=one_time`.
- Switching plan toggle in paywall re-quotes any applied coupon (or shows "wrong target" error).

**Regression:**
- v1 subscribers without any coupon code see no UI change — coupon section is collapsed by default.
- v1 monthly subscription endpoint with no `coupon_code` param behaves identically.

---

## G. Sequencing (v1.1 build order)

1. **Data layer** — models, migration, seed scripts. Validate with raw SQL: insert a coupon, query it, insert a redemption, assert unique constraint blocks dup.
2. **Coupon service + `/billing/coupons/validate` endpoint** — pure logic, no payment processor. Unit tests.
3. **One-time Razorpay path** — order create + verify endpoints, web paywall plan toggle + coupon input. Test EARLYACCESS = 0 free-grant first (no Razorpay touched), then ₹200 paid flow.
4. **Monthly with Razorpay Offer** — sync EARLYSALE offer to Razorpay, modify subscription create, webhook redemption recording. Test in Razorpay test mode.
5. **iOS one-time IAP** — add product to App Store Connect + `.storekit`, `purchaseOneTime`, paywall plan picker. Sandbox test.
6. **iOS EARLYSALE Promotional Offer** — App Store Connect offer + signing key, `/apple/redeem-offer` endpoint, `purchaseMonthly(withPromotionalOffer:)`. Sandbox test.
7. **Expiry UX polish** — `OneTimeExpiryBanner` on both platforms, "Switch to monthly" CTA on subscription pages.
