-- Casepilot: distinguish replay-generated traces from primary investigations
-- Applied via: make migrate

ALTER TABLE run_traces ADD COLUMN IF NOT EXISTS is_replay BOOLEAN NOT NULL DEFAULT false;

-- Partial index — primary traces are the common filter target
CREATE INDEX IF NOT EXISTS idx_run_traces_primary ON run_traces(issue_id, started_at DESC)
    WHERE is_replay = false;
