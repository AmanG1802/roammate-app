-- Migration: Convert day_date columns from DATE to VARCHAR
-- Reason: Eliminate timezone ambiguity across DB, backend, iOS, and web frontends.
-- PostgreSQL DATE::text produces "YYYY-MM-DD" natively.
-- Indexes are rebuilt automatically by ALTER TYPE.

BEGIN;

ALTER TABLE timeline_item
  ALTER COLUMN day_date TYPE VARCHAR USING day_date::text;

ALTER TABLE day_route
  ALTER COLUMN day_date TYPE VARCHAR USING day_date::text;

COMMIT;
