-- Casepilot: replay engine schema
-- Applied via: make migrate

CREATE TABLE IF NOT EXISTS replay_sessions (
    session_id       TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::text,
    trace_id         TEXT        NOT NULL UNIQUE REFERENCES run_traces(trace_id),
    issue_id         TEXT        NOT NULL REFERENCES issues(issue_id),
    n_runs           INTEGER     NOT NULL DEFAULT 3,
    matches          INTEGER     NOT NULL DEFAULT 0,
    stability_score  NUMERIC(4,3),
    status           TEXT        NOT NULL DEFAULT 'running',  -- running|completed|failed
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS replay_runs (
    run_id            TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id        TEXT        NOT NULL REFERENCES replay_sessions(session_id),
    replay_trace_id   TEXT        REFERENCES run_traces(trace_id),
    perturbation      TEXT        NOT NULL,
    resolution_type   TEXT,
    confidence_score  NUMERIC(4,3),
    escalate          BOOLEAN,
    matches_original  BOOLEAN,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_replay_sessions_trace   ON replay_sessions(trace_id);
CREATE INDEX IF NOT EXISTS idx_replay_sessions_issue   ON replay_sessions(issue_id);
CREATE INDEX IF NOT EXISTS idx_replay_runs_session     ON replay_runs(session_id);
