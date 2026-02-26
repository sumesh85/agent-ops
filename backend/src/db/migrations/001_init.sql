-- Casepilot: initial schema
-- Applied automatically by PostgreSQL on first container start

-- ── Customers ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    customer_id     TEXT        PRIMARY KEY,
    name            TEXT        NOT NULL,
    email           TEXT        NOT NULL UNIQUE,
    province        TEXT        NOT NULL,
    date_of_birth   DATE,
    kyc_status      TEXT        NOT NULL DEFAULT 'pending',   -- verified|pending|flagged|expired
    kyc_verified_at TIMESTAMPTZ,
    kyc_expires_at  TIMESTAMPTZ,
    risk_profile    TEXT        NOT NULL DEFAULT 'balanced',  -- conservative|balanced|growth
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Accounts ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    account_id              TEXT        PRIMARY KEY,
    customer_id             TEXT        NOT NULL REFERENCES customers(customer_id),
    account_type            TEXT        NOT NULL,  -- TFSA|RRSP|FHSA|Cash|Crypto
    account_number          TEXT        NOT NULL UNIQUE,
    status                  TEXT        NOT NULL DEFAULT 'active',  -- active|frozen|restricted|closed
    freeze_reason           TEXT,                                   -- AML_REVIEW|KYC_EXPIRED|FRAUD_HOLD|null
    balance                 NUMERIC(14,2) NOT NULL DEFAULT 0,
    available_balance       NUMERIC(14,2) NOT NULL DEFAULT 0,
    currency                TEXT        NOT NULL DEFAULT 'CAD',
    rrsp_contribution_ytd   NUMERIC(14,2) NOT NULL DEFAULT 0,
    tfsa_contribution_ytd   NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);

-- ── Transactions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   TEXT          PRIMARY KEY,
    account_id       TEXT          NOT NULL REFERENCES accounts(account_id),
    transaction_type TEXT          NOT NULL,
    -- deposit|withdrawal|wire_in|wire_out|transfer_in|transfer_out
    -- trade_buy|trade_sell|dividend|drip|etransfer
    amount           NUMERIC(14,2) NOT NULL,
    currency         TEXT          NOT NULL DEFAULT 'CAD',
    status           TEXT          NOT NULL,
    -- completed|pending|processing|failed|reversed|pending_reversal
    description      TEXT,
    counterparty     TEXT,
    reference_number TEXT,
    failure_reason   TEXT,
    initiated_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    settled_at       TIMESTAMPTZ,
    metadata         JSONB         NOT NULL DEFAULT '{}'
    -- {device_id, ip_country, instrument, quantity, unit_price, login_session_id}
);

CREATE INDEX IF NOT EXISTS idx_transactions_account  ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type     ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_status   ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_initiated ON transactions(initiated_at DESC);

-- ── Login Events ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS login_events (
    event_id    TEXT        PRIMARY KEY,
    customer_id TEXT        NOT NULL REFERENCES customers(customer_id),
    event_type  TEXT        NOT NULL,  -- login|logout|failed_attempt
    device_id   TEXT,
    ip_address  TEXT,
    ip_country  TEXT,
    user_agent  TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_events_customer ON login_events(customer_id);
CREATE INDEX IF NOT EXISTS idx_login_events_occurred ON login_events(occurred_at DESC);

-- ── Communications ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS communications (
    comm_id      TEXT        PRIMARY KEY,
    customer_id  TEXT        NOT NULL REFERENCES customers(customer_id),
    direction    TEXT        NOT NULL,  -- inbound|outbound
    channel      TEXT        NOT NULL,  -- email|sms|push
    subject      TEXT,
    body_summary TEXT,
    sent_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_communications_customer ON communications(customer_id);

-- ── Historical Cases (for similarity search seeding) ─────────────────────────
CREATE TABLE IF NOT EXISTS cases (
    case_id                  TEXT          PRIMARY KEY,
    customer_id              TEXT          REFERENCES customers(customer_id),
    issue_type               TEXT          NOT NULL,
    -- WIRE_DELAY|ACCOUNT_FROZEN|RRSP_OVER|TAX_SLIP|UNAUTH_TRADE|ETRANSFER_FAIL|KYC_EXPIRED
    issue_description        TEXT          NOT NULL,
    investigation_steps      JSONB         NOT NULL DEFAULT '[]',
    root_cause               TEXT,
    resolution               TEXT,
    resolution_type          TEXT,  -- AUTO_RESOLVED|ESCALATED|REFUNDED|CORRECTED
    confidence_score         NUMERIC(4,3),
    time_to_resolve_hours    NUMERIC(6,2),
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    resolved_at              TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cases_issue_type ON cases(issue_type);

-- ── Incoming Issues (agent processes these) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS issues (
    issue_id    TEXT        PRIMARY KEY,
    customer_id TEXT        NOT NULL REFERENCES customers(customer_id),
    raw_message TEXT        NOT NULL,
    channel     TEXT        NOT NULL DEFAULT 'chat',  -- chat|email|phone_transcript
    urgency     TEXT        NOT NULL DEFAULT 'medium', -- low|medium|high|critical
    status      TEXT        NOT NULL DEFAULT 'open',  -- open|investigating|resolved|escalated
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Agent Run Traces (control plane observability) ────────────────────────────
CREATE TABLE IF NOT EXISTS run_traces (
    trace_id          TEXT          PRIMARY KEY,
    issue_id          TEXT          REFERENCES issues(issue_id),
    started_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    completed_at      TIMESTAMPTZ,
    status            TEXT          NOT NULL DEFAULT 'running',
    -- running|completed|escalated|failed
    tool_calls        JSONB         NOT NULL DEFAULT '[]',
    -- [{tool, args_digest, latency_ms, result_summary}]
    agent_reasoning   TEXT,
    structured_output JSONB,
    confidence_score  NUMERIC(4,3),
    escalate          BOOLEAN       NOT NULL DEFAULT FALSE,
    policy_flags      JSONB         NOT NULL DEFAULT '[]',
    -- [{flag_type, triggered_by, severity}]
    token_count       INTEGER,
    model             TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_traces_issue   ON run_traces(issue_id);
CREATE INDEX IF NOT EXISTS idx_run_traces_started ON run_traces(started_at DESC);
