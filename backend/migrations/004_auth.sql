-- Migration: Auth refactor — Google + Apple OAuth, email verification, refresh tokens
-- Reason: Replace single-method password auth with multi-provider sign-in,
-- introduce mandatory email verification, and rotate-on-use refresh tokens.

BEGIN;

-- 1. User auth columns
ALTER TABLE "user"
  ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS auth_version INTEGER NOT NULL DEFAULT 1;

-- 2. Linked OAuth identities (google | apple)
CREATE TABLE IF NOT EXISTS user_identity (
  id              BIGSERIAL PRIMARY KEY,
  user_id         INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  provider        VARCHAR(16) NOT NULL,
  subject         VARCHAR(255) NOT NULL,
  email_at_link   VARCHAR(320),
  created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_user_identity_user_id ON user_identity (user_id);
ALTER TABLE user_identity
  ADD CONSTRAINT uq_user_identity_provider_subject UNIQUE (provider, subject);

-- 3. Email verification tokens (signup + email change)
CREATE TABLE IF NOT EXISTS email_verification (
  token_hash      VARCHAR(64) PRIMARY KEY,            -- sha256 hex
  user_id         INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  email           VARCHAR(320) NOT NULL,
  purpose         VARCHAR(24) NOT NULL,               -- 'signup' | 'change_email'
  expires_at      TIMESTAMP WITH TIME ZONE NOT NULL,
  consumed_at     TIMESTAMP WITH TIME ZONE,
  created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_email_verification_user_id ON email_verification (user_id);

-- 4. Password reset tokens
CREATE TABLE IF NOT EXISTS password_reset (
  token_hash      VARCHAR(64) PRIMARY KEY,            -- sha256 hex
  user_id         INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  expires_at      TIMESTAMP WITH TIME ZONE NOT NULL,
  consumed_at     TIMESTAMP WITH TIME ZONE,
  created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_password_reset_user_id ON password_reset (user_id);

-- 5. Refresh tokens (opaque, hashed, rotation chain)
CREATE TABLE IF NOT EXISTS refresh_token (
  id              BIGSERIAL PRIMARY KEY,
  user_id         INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  token_hash      VARCHAR(64) NOT NULL UNIQUE,        -- sha256 hex
  device_label    VARCHAR(128),
  parent_id       BIGINT REFERENCES refresh_token(id) ON DELETE SET NULL,
  expires_at      TIMESTAMP WITH TIME ZONE NOT NULL,
  revoked_at      TIMESTAMP WITH TIME ZONE,
  last_used_at    TIMESTAMP WITH TIME ZONE,
  created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_refresh_token_user_id ON refresh_token (user_id);

-- Backfill: existing users keep email_verified=false; the legacy login endpoint
-- returns a flag the new clients use to push them through a one-time verify
-- flow. After the deprecation window the legacy endpoint is removed.

COMMIT;
