-- 010_concierge_action.sql
-- Phase 8 (3.8): undo last Concierge action.
-- Records an inverse patch for each confirmed mutation so it can be reverted.
-- Mirrored by auto_migrate.sync_schema (create_all for new tables); this file
-- keeps the production/raw-SQL path in sync.

CREATE TABLE IF NOT EXISTS concierge_action (
    id            SERIAL PRIMARY KEY,
    trip_id       INTEGER NOT NULL REFERENCES trip(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    intent        VARCHAR NOT NULL,
    inverse_patch JSON,
    created_at    TIMESTAMPTZ DEFAULT now(),
    undone_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_concierge_action_trip_id ON concierge_action (trip_id);
CREATE INDEX IF NOT EXISTS ix_concierge_action_user_id ON concierge_action (user_id);
CREATE INDEX IF NOT EXISTS ix_concierge_action_created_at ON concierge_action (created_at);
