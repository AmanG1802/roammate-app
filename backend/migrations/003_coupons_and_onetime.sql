-- Migration: Coupon system + one-time payment support (v1.1)
-- Reason: Add EARLYACCESS / EARLYSALE promo codes and ₹200 one-time-purchase
-- (30-day Plus grant) flow. Backend owns one-time math; Razorpay Offers and
-- Apple Promotional Offers handle subscription first-cycle discounts.

BEGIN;

-- 1. User columns for one-time tracking
ALTER TABLE "user"
  ADD COLUMN IF NOT EXISTS last_one_time_purchase_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS last_one_time_external_id VARCHAR;

-- 2. Coupon catalog
CREATE TABLE IF NOT EXISTS coupon (
  id SERIAL PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR,
  discount_type VARCHAR(16) NOT NULL,        -- "flat_off" | "percent_off" | "fixed_price"
  discount_value INTEGER NOT NULL,
  applies_to VARCHAR(32) NOT NULL,           -- "one_time" | "subscription_first_cycle" | "any"
  valid_from TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
  max_redemptions_per_user INTEGER NOT NULL DEFAULT 1,
  razorpay_offer_id VARCHAR,
  apple_offer_id VARCHAR,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_coupon_code ON coupon (code);

-- 3. Per-user coupon redemption ledger
CREATE TABLE IF NOT EXISTS coupon_redemption (
  id SERIAL PRIMARY KEY,
  coupon_id INTEGER NOT NULL REFERENCES coupon(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  provider VARCHAR(24) NOT NULL,             -- "razorpay" | "apple" | "internal_grant"
  payment_external_id VARCHAR,
  amount_paid_paise INTEGER NOT NULL DEFAULT 0,
  applied_at_period_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_coupon_redemption_user ON coupon_redemption (user_id);
ALTER TABLE coupon_redemption
  ADD CONSTRAINT uq_coupon_redemption_coupon_user
  UNIQUE (coupon_id, user_id);

-- 4. Seed launch coupons (idempotent via UNIQUE(code))
INSERT INTO coupon (code, description, discount_type, discount_value, applies_to, valid_from, valid_until, max_redemptions_per_user, is_active)
VALUES
  ('EARLYACCESS',
   'Free 30 days of Roammate Plus for early-access users',
   'flat_off', 20000, 'one_time',
   NOW(), NOW() + INTERVAL '90 days', 1, TRUE),
  ('EARLYSALE',
   'First month of Roammate Plus at ₹49, then ₹149/month',
   'fixed_price', 4900, 'subscription_first_cycle',
   NOW(), NOW() + INTERVAL '60 days', 1, TRUE)
ON CONFLICT (code) DO NOTHING;

COMMIT;
