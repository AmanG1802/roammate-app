-- Migration 008: store Apple SIWA refresh token for Guideline 5.1.1(v) revocation
ALTER TABLE user_identity
    ADD COLUMN IF NOT EXISTS apple_refresh_token VARCHAR(2048);
