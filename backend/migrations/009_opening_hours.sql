-- Migration: add opening_hours to place-bearing tables
-- Reason: the Concierge + Smart Ripple engines warn when a (possibly shifted)
-- event falls outside its venue's opening/closing hours. The hours are enriched
-- from Google Places (regularOpeningHours) and stored as JSON on every
-- place-bearing row, via the shared PlaceColumnsMixin / PLACE_FIELDS.
--
-- Gated at the enrichment layer by GOOGLE_MAPS_FETCH_OPENING_HOURS; the column
-- is always present (nullable) so a flag flip needs no schema change.
--
-- Additive + nullable, so app/db/auto_migrate.py also adds these at startup;
-- this file mirrors that for environments that apply the numbered SQL set.

BEGIN;

ALTER TABLE timeline_item     ADD COLUMN IF NOT EXISTS opening_hours JSON;
ALTER TABLE idea_bin_item     ADD COLUMN IF NOT EXISTS opening_hours JSON;
ALTER TABLE brainstorm_bin_item ADD COLUMN IF NOT EXISTS opening_hours JSON;

COMMIT;
