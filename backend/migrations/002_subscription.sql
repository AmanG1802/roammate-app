-- Migration: Roammate Plus subscription tables and User fields
-- Reason: Introduce paid tier with free/Plus entitlements, Razorpay (web) +
-- Apple IAP (iOS) integration, and per-user monthly usage counters.

BEGIN;

-- 1. User subscription columns
ALTER TABLE "user"
  ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(16) NOT NULL DEFAULT 'free',
  ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(24) NOT NULL DEFAULT 'none',
  ADD COLUMN IF NOT EXISTS subscription_provider VARCHAR(16),
  ADD COLUMN IF NOT EXISTS subscription_current_period_end TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS subscription_external_id VARCHAR;

CREATE INDEX IF NOT EXISTS ix_user_subscription_external_id
  ON "user" (subscription_external_id);

-- 2. Subscription event audit log
CREATE TABLE IF NOT EXISTS subscription_event (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
  provider VARCHAR(16) NOT NULL,
  event_id VARCHAR NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  raw_payload JSON NOT NULL DEFAULT '{}'::json,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_subscription_event_user_id
  ON subscription_event (user_id);
CREATE INDEX IF NOT EXISTS ix_subscription_event_user_created
  ON subscription_event (user_id, created_at);
ALTER TABLE subscription_event
  ADD CONSTRAINT uq_subscription_event_provider_event
  UNIQUE (provider, event_id);

-- 3. Per-user monthly usage counter
CREATE TABLE IF NOT EXISTS usage_counter (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  period VARCHAR(7) NOT NULL,                -- "YYYY-MM"
  brainstorm_messages INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_usage_counter_user_id
  ON usage_counter (user_id);
ALTER TABLE usage_counter
  ADD CONSTRAINT uq_usage_counter_user_period
  UNIQUE (user_id, period);

COMMIT;
