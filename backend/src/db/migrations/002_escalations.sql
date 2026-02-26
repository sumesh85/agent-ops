-- AgentOps: escalation review queue
-- Applied automatically by the backend on startup (idempotent)

CREATE TABLE IF NOT EXISTS escalation_reviews (
    review_id    TEXT        PRIMARY KEY DEFAULT gen_random_uuid()::text,
    trace_id     TEXT        NOT NULL UNIQUE REFERENCES run_traces(trace_id),
    issue_id     TEXT        NOT NULL REFERENCES issues(issue_id),
    reviewer     TEXT        NOT NULL DEFAULT 'human_agent',
    decision     TEXT        NOT NULL,  -- approved|overridden|rejected
    notes        TEXT,
    reviewed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escalation_reviews_trace    ON escalation_reviews(trace_id);
CREATE INDEX IF NOT EXISTS idx_escalation_reviews_issue    ON escalation_reviews(issue_id);
CREATE INDEX IF NOT EXISTS idx_escalation_reviews_reviewed ON escalation_reviews(reviewed_at DESC);
