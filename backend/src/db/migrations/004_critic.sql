-- AgentOps: critic model fields on run_traces
-- Applied via: make migrate

ALTER TABLE run_traces ADD COLUMN IF NOT EXISTS critic_agrees BOOLEAN;
ALTER TABLE run_traces ADD COLUMN IF NOT EXISTS critic_notes  TEXT;
ALTER TABLE run_traces ADD COLUMN IF NOT EXISTS critic_model  TEXT;
