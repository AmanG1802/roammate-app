-- Migration: tutorial onboarding state
-- Adds per-trip tutorial flags and per-platform tutorial progress on the user.
--   trips.is_tutorial             — single source of truth for canned/bypass paths
--   trips.is_tutorial_completed   — locks the trip read-only after the tour ends
--   users.tutorial_status_{web,ios} — not_started | in_progress | completed | skipped
--   users.tutorial_step_{web,ios}  — current 1..N step (0 before start)
-- A partial unique index enforces "at most one active tutorial trip per user".

BEGIN;

ALTER TABLE trip
  ADD COLUMN IF NOT EXISTS is_tutorial BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS is_tutorial_completed BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_tutorial_trip
  ON trip(created_by_id)
  WHERE is_tutorial = TRUE;

ALTER TABLE "user"
  ADD COLUMN IF NOT EXISTS tutorial_status_web VARCHAR(20) NOT NULL DEFAULT 'not_started',
  ADD COLUMN IF NOT EXISTS tutorial_status_ios VARCHAR(20) NOT NULL DEFAULT 'not_started',
  ADD COLUMN IF NOT EXISTS tutorial_step_web INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS tutorial_step_ios INT NOT NULL DEFAULT 0;

COMMIT;
