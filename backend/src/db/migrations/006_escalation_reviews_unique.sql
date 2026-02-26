-- Casepilot: add missing UNIQUE constraint on escalation_reviews.trace_id
-- The table was created before migrations moved out of app startup,
-- so CREATE TABLE IF NOT EXISTS skipped the constraint.
-- Applied via: make migrate

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'escalation_reviews_trace_id_key'
          AND conrelid = 'escalation_reviews'::regclass
    ) THEN
        ALTER TABLE escalation_reviews
            ADD CONSTRAINT escalation_reviews_trace_id_key UNIQUE (trace_id);
    END IF;
END $$;
