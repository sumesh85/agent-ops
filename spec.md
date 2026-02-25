SQLite Schema                                                                                                                                            
                                                                                                                                                           
  customers                                                                                                                                                
                                                                                                                                                           
  CREATE TABLE customers (                                                                                                                               
      customer_id     TEXT PRIMARY KEY,                                                                                                                    
      name            TEXT,                                                                                                                                
      email           TEXT,
      province        TEXT,           -- affects tax rules
      date_of_birth   DATE,
      kyc_status      TEXT,           -- verified | pending | flagged | expired
      risk_profile    TEXT,           -- conservative | balanced | growth
      created_at      TIMESTAMP
  );

  accounts

  CREATE TABLE accounts (
      account_id              TEXT PRIMARY KEY,
      customer_id             TEXT REFERENCES customers,
      account_type            TEXT,   -- TFSA | RRSP | FHSA | Cash | Crypto
      account_number          TEXT,
      status                  TEXT,   -- active | frozen | restricted | closed
      freeze_reason           TEXT,   -- AML_REVIEW | KYC_EXPIRED | FRAUD_HOLD | null
      balance                 REAL,
      available_balance       REAL,
      currency                TEXT,
      rrsp_contribution_ytd   REAL,
      tfsa_contribution_ytd   REAL,
      created_at              TIMESTAMP
  );

  transactions

  CREATE TABLE transactions (
      transaction_id      TEXT PRIMARY KEY,
      account_id          TEXT REFERENCES accounts,
      transaction_type    TEXT,   -- deposit | withdrawal | wire_in | wire_out |
                                  -- transfer_in | transfer_out | trade_buy |
                                  -- trade_sell | dividend | drip | etransfer
      amount              REAL,
      currency            TEXT,
      status              TEXT,   -- completed | pending | processing | failed | reversed
      description         TEXT,
      counterparty        TEXT,
      reference_number    TEXT,
      failure_reason      TEXT,   -- nullable
      initiated_at        TIMESTAMP,
      settled_at          TIMESTAMP,  -- nullable
      metadata            JSON        -- device_id, ip_country, instrument, etc.
  );

  cases (historical — for ML similarity)

  CREATE TABLE cases (
      case_id                 TEXT PRIMARY KEY,
      customer_id             TEXT REFERENCES customers,
      issue_type              TEXT,   -- WIRE_DELAY | ACCOUNT_FROZEN | RRSP_OVER |
                                      -- TAX_SLIP | UNAUTH_TRADE | ETRANSFER_FAIL
      issue_description       TEXT,
      investigation_steps     JSON,   -- ordered list of tools called + findings
      root_cause              TEXT,
      resolution              TEXT,
      resolution_type         TEXT,   -- AUTO_RESOLVED | ESCALATED | REFUNDED | CORRECTED
      confidence_score        REAL,   -- 0.0-1.0
      time_to_resolve_hours   REAL,
      created_at              TIMESTAMP,
      resolved_at             TIMESTAMP
  );

  issues (incoming — agent processes these)

  CREATE TABLE issues (
      issue_id        TEXT PRIMARY KEY,
      customer_id     TEXT REFERENCES customers,
      raw_message     TEXT,       -- free text from customer
      channel         TEXT,       -- chat | email | phone_transcript
      urgency         TEXT,       -- low | medium | high | critical
      status          TEXT,       -- open | investigating | resolved | escalated
      created_at      TIMESTAMP
  );

  ---
  ChromaDB Collections (Policy Docs)

  policies/
  ├── wire_transfers.md        -- processing times, failure codes, AML holds
  ├── rrsp_rules.md            -- contribution limits, room calculation, penalties
  ├── tfsa_rules.md            -- annual limits, over-contribution rules
  ├── account_security.md      -- freeze triggers, fraud response, unauthorized access
  ├── etransfer_policy.md      -- failure handling, refund timelines
  ├── tax_slips.md             -- T5, T5008, DRIP treatment, RRSP receipts
  ├── kyc_compliance.md        -- verification requirements, expiry, renewal steps
  └── trading_policies.md      -- order types, settlement, dispute window

  Each doc uses publicly available CRA + standard fintech policy patterns. No real Wealthsimple IP needed.

  ---
  6 Demo Scenarios

  Ordered by ascending complexity and designed to stress-test different reasoning paths.

  ---
  Scenario 1 — Wire Transfer Delay + Silent Freeze

  Issue: "My $15,000 wire from TD hasn't arrived in 4 days and my account seems partially restricted. I need this money urgently."

  Why AI-native: Two unconnected systems (transaction + compliance) need to be correlated.

  ┌──────┬───────────────────────────────────────────┬─────────────────────────────────────────────────┐
  │ Step │                   Tool                    │                     Finding                     │
  ├──────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤
  │ 1    │ account.lookup                            │ Status: RESTRICTED, freeze_reason: AML_REVIEW   │
  ├──────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤
  │ 2    │ transactions.search                       │ Wire in status: PROCESSING, day 4               │
  ├──────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤
  │ 3    │ policy.search("wire processing AML hold") │ Large inbound wires trigger 3-5 day AML review  │
  ├──────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤
  │ 4    │ cases.similar                             │ 3 similar cases resolved automatically on day 5 │
  └──────┴───────────────────────────────────────────┴─────────────────────────────────────────────────┘

  Output: Auto-resolved. Explains the AML hold is triggered by wire size, not fraud. Expected clearance: 1 day. Confidence: 87%.

  ---
  Scenario 2 — RRSP Over-contribution Risk

  Issue: "I just put $20,000 into my RRSP but got a warning email. Am I going to be penalized by CRA?"

  Why AI-native: Requires calculating contribution room from multiple data points — prior contributions, carry-forward room, employer pension adjustment.

  ┌──────┬───────────────────────────────────────────────┬───────────────────────────────────────────────────┐
  │ Step │                     Tool                      │                      Finding                      │
  ├──────┼───────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ 1    │ account.lookup                                │ RRSP account, rrsp_contribution_ytd: $29,500      │
  ├──────┼───────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ 2    │ transactions.search                           │ Finds $20,000 deposit + $9,500 earlier in year    │
  ├──────┼───────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ 3    │ policy.search("RRSP contribution limit 2025") │ 2025 limit: $31,560                               │
  ├──────┼───────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ 4    │ customer.lookup                               │ Province: ON, prior year NOA data (synthetic)     │
  ├──────┼───────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ 5    │ cases.similar                                 │ Similar case — DRIP incorrectly counted, resolved │
  └──────┴───────────────────────────────────────────────┴───────────────────────────────────────────────────┘

  Output: Escalate to human advisor. Agent finds customer is $1,940 over-limit but cannot confirm prior-year unused room without NOA. Confidence too low to
   auto-resolve. Flags risk of 1% CRA penalty per month. Confidence: 54%.

  Key demo moment: Agent explicitly says "I cannot make a tax determination without confirming prior-year contribution room — escalating with full evidence
   summary."

  ---
  Scenario 3 — Suspected Unauthorized Trade

  Issue: "I see a sell order on my Apple shares that I never placed. I think someone accessed my account."

  Why AI-native: Security signal correlation — trade metadata, login history, device fingerprint all live in different places.

  ┌──────┬─────────────────────────────────────────────────┬─────────────────────────────────────────────┐
  │ Step │                      Tool                       │                   Finding                   │
  ├──────┼─────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ 1    │ account.lookup                                  │ Status: active, no freeze                   │
  ├──────┼─────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ 2    │ transactions.search                             │ Sell trade $8,400, initiated 2 AM, settled  │
  ├──────┼─────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ 3    │ transactions.metadata                           │ Device: unknown, IP country: Romania        │
  ├──────┼─────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ 4    │ account.login_history                           │ Login from Romania 90 min before trade      │
  ├──────┼─────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ 5    │ policy.search("unauthorized transaction fraud") │ Mandatory escalation + immediate freeze     │
  ├──────┼─────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ 6    │ cases.similar                                   │ 2 identical patterns — both confirmed fraud │
  └──────┴─────────────────────────────────────────────────┴─────────────────────────────────────────────┘

  Output: Critical escalation. Agent immediately flags for security team, recommends account freeze, drafts customer communication. Does not attempt to
  resolve. Confidence: 96% unauthorized.

  Key demo moment: Agent hits a hard policy boundary — it refuses to auto-resolve and escalates regardless of confidence score.

  ---
  Scenario 4 — Tax Slip Discrepancy (T5 vs. Actual Dividends)

  Issue: "My T5 shows $1,200 in dividends but my own records show only $890. My tax return is due soon."

  Why AI-native: Agent must understand that DRIP transactions are taxable dividend income — not obvious from transaction labels.

  ┌──────┬─────────────────────────────────────────────────┬───────────────────────────────────────────┐
  │ Step │                      Tool                       │                  Finding                  │
  ├──────┼─────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ 1    │ account.lookup                                  │ Cash + TFSA accounts                      │
  ├──────┼─────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ 2    │ transactions.search(type=dividend, year=2024)   │ $890 in cash dividends                    │
  ├──────┼─────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ 3    │ transactions.search(type=drip, year=2024)       │ $310 in DRIP reinvestment                 │
  ├──────┼─────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ 4    │ policy.search("DRIP dividend reinvestment tax") │ DRIP is taxable dividend income per CRA   │
  ├──────┼─────────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ 5    │ Calculate                                       │ $890 + $310 = $1,200 — matches T5 exactly │
  └──────┴─────────────────────────────────────────────────┴───────────────────────────────────────────┘

  Output: Auto-resolved. Explains DRIP treatment, provides breakdown, suggests customer update their own records. Confidence: 97%.

  Key demo moment: The gap between what the customer sees and what's taxable is bridged by policy reasoning, not a lookup.

  ---
  Scenario 5 — Failed E-Transfer + Missing Refund

  Issue: "I sent $500 to my friend, it failed, the money was taken twice. Only one refund came back."

  Why AI-native: Requires correlating multiple transaction states — debit, failure, refund, and pending reversal — across time.

  ┌──────┬────────────────────────────────────────────┬──────────────────────────────────────────────────┐
  │ Step │                    Tool                    │                     Finding                      │
  ├──────┼────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 1    │ account.lookup                             │ Active, available balance lower than expected    │
  ├──────┼────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 2    │ transactions.search(type=etransfer)        │ Two $500 debits, both FAILED                     │
  ├──────┼────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 3    │ Check refunds                              │ One REVERSED (+$500), one PENDING_REVERSAL       │
  ├──────┼────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 4    │ policy.search("etransfer refund timeline") │ Pending reversals process in 1-3 business days   │
  ├──────┼────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ 5    │ cases.similar                              │ 5 identical — all resolved when reversal cleared │
  └──────┴────────────────────────────────────────────┴──────────────────────────────────────────────────┘

  Output: Auto-resolved. Explains second refund is in pipeline, gives expected date. Confidence: 92%.

  ---
  Scenario 6 — Account Frozen: KYC Expired

  Issue: "My account is completely locked. I can't do anything. What's happening?"

  Why AI-native: Multiple sub-questions must be answered in sequence: why frozen, when did it expire, what was communicated, what does the customer need to
   do.

  ┌──────┬────────────────────────────────────────┬─────────────────────────────────────────────────────────┐
  │ Step │                  Tool                  │                         Finding                         │
  ├──────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ 1    │ account.lookup                         │ Status: FROZEN, freeze_reason: KYC_EXPIRED              │
  ├──────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ 2    │ customer.lookup                        │ KYC expired 32 days ago                                 │
  ├──────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ 3    │ account.communication_history          │ 3 reminder emails sent, no response                     │
  ├──────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ 4    │ policy.search("KYC renewal documents") │ ID + proof of address, varies by account type           │
  ├──────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ 5    │ Check account types                    │ TFSA + RRSP — requires government ID + SIN confirmation │
  └──────┴────────────────────────────────────────┴─────────────────────────────────────────────────────────┘

  Output: Auto-resolved with step-by-step instructions. Lists exact documents needed, upload link, expected unfreeze timeline (24-48h after submission).
  Confidence: 99%.

  ---
  Coverage Matrix

  ┌───────────────────┬──────────────────┬───────────────────┬───────────────────────────────┬─────────────────────┐
  │     Scenario      │    Issue Type    │    Resolution     │         Key Reasoning         │    ML Component     │
  ├───────────────────┼──────────────────┼───────────────────┼───────────────────────────────┼─────────────────────┤
  │ 1 — Wire + Freeze │ Wire delay       │ Auto              │ Cross-system correlation      │ Similarity match    │
  ├───────────────────┼──────────────────┼───────────────────┼───────────────────────────────┼─────────────────────┤
  │ 2 — RRSP Over     │ Tax/contribution │ Escalate          │ Calculation under uncertainty │ Risk scoring        │
  ├───────────────────┼──────────────────┼───────────────────┼───────────────────────────────┼─────────────────────┤
  │ 3 — Unauth Trade  │ Security/fraud   │ Critical escalate │ Signal correlation            │ Fraud pattern match │
  ├───────────────────┼──────────────────┼───────────────────┼───────────────────────────────┼─────────────────────┤
  │ 4 — T5 Gap        │ Tax slip         │ Auto              │ Policy interpretation         │ None                │
  ├───────────────────┼──────────────────┼───────────────────┼───────────────────────────────┼─────────────────────┤
  │ 5 — E-Transfer    │ Failed payment   │ Auto              │ Transaction state machine     │ Similarity match    │
  ├───────────────────┼──────────────────┼───────────────────┼───────────────────────────────┼─────────────────────┤
  │ 6 — KYC Frozen    │ Compliance       │ Auto + guided     │ Multi-step process resolution │ None                │
  └───────────────────┴──────────────────┴───────────────────┴───────────────────────────────┴─────────────────────┘

  ---
  Generation Approach

  # tools needed
  faker          # account/customer/transaction records
  uuid           # IDs
  sqlite3        # local DB
  chromadb       # policy vector store
  anthropic      # generate realistic issue messages + case histories

  Generate in this order:
  1. Customers (10 records)
  2. Accounts (2-3 per customer)
  3. Transactions (30-50 per account, last 18 months)
  4. Historical cases (50-100 for similarity matching)
  5. Policy docs (8 markdown files → embed into ChromaDB)
  6. Issues (6 — one per demo scenario)