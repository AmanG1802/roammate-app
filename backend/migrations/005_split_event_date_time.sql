-- Migration: split TimelineItem/IdeaBinItem time columns
-- Reason: day_date (VARCHAR) and start_time/end_time (TIMESTAMPTZ) were
-- written independently, so the calendar date inside start_time could drift
-- away from day_date (see docs/[27]). Fix at the schema level:
--   day_date           VARCHAR → DATE
--   start_time/end_time TIMESTAMPTZ → TIME (trip-local wall-clock)
--
-- The backfill uses `AT TIME ZONE trip.timezone` so existing rows keep the
-- wall-clock time the user already sees; cross-tz trips with the wrong
-- Trip.timezone should be corrected via the new tz picker before running this.
--
-- Overnight events (end < start) are not supported in v1; the CHECK
-- constraints make that invariant explicit.

BEGIN;

-- ─── timeline_item ──────────────────────────────────────────────────────────

ALTER TABLE timeline_item
  ADD COLUMN day_date_new   DATE,
  ADD COLUMN start_time_new TIME,
  ADD COLUMN end_time_new   TIME;

UPDATE timeline_item ti
SET day_date_new = NULLIF(ti.day_date, '')::date,
    start_time_new = (ti.start_time AT TIME ZONE COALESCE(t.timezone, 'UTC'))::time,
    end_time_new   = (ti.end_time   AT TIME ZONE COALESCE(t.timezone, 'UTC'))::time
FROM trip t
WHERE ti.trip_id = t.id;

ALTER TABLE timeline_item
  DROP COLUMN day_date,
  DROP COLUMN start_time,
  DROP COLUMN end_time;

ALTER TABLE timeline_item
  RENAME COLUMN day_date_new TO day_date;
ALTER TABLE timeline_item
  RENAME COLUMN start_time_new TO start_time;
ALTER TABLE timeline_item
  RENAME COLUMN end_time_new TO end_time;

ALTER TABLE timeline_item
  ADD CONSTRAINT timeline_item_no_overnight
  CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time);

CREATE INDEX IF NOT EXISTS ix_timeline_item_day_date
  ON timeline_item (day_date);
CREATE INDEX IF NOT EXISTS ix_timeline_item_trip_day_start
  ON timeline_item (trip_id, day_date, start_time);

-- ─── idea_bin_item ──────────────────────────────────────────────────────────

ALTER TABLE idea_bin_item
  ADD COLUMN start_time_new TIME,
  ADD COLUMN end_time_new   TIME;

UPDATE idea_bin_item ib
SET start_time_new = (ib.start_time AT TIME ZONE COALESCE(t.timezone, 'UTC'))::time,
    end_time_new   = (ib.end_time   AT TIME ZONE COALESCE(t.timezone, 'UTC'))::time
FROM trip t
WHERE ib.trip_id = t.id;

ALTER TABLE idea_bin_item
  DROP COLUMN start_time,
  DROP COLUMN end_time;

ALTER TABLE idea_bin_item
  RENAME COLUMN start_time_new TO start_time;
ALTER TABLE idea_bin_item
  RENAME COLUMN end_time_new TO end_time;

ALTER TABLE idea_bin_item
  ADD CONSTRAINT idea_bin_item_no_overnight
  CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time);

COMMIT;
