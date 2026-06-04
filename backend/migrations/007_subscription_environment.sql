-- Migration: Track Apple sandbox vs production environment per user
-- Reason: With server-side JWS verification enabled, sandbox and production
-- transaction IDs are now distinguishable; storing the environment lets
-- admin tooling separate test purchases from real ones and prevents future
-- cross-environment ID collisions.

BEGIN;

ALTER TABLE "user"
  ADD COLUMN IF NOT EXISTS subscription_environment VARCHAR(16);

COMMIT;
