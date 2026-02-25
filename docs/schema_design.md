# Data Schema Design
# Financial Issue Investigation Agent — AgentOps MVP

---

## Storage Overview

| Store     | Purpose                                     | Technology |
|-----------|---------------------------------------------|------------|
| SQLite    | Customers, accounts, transactions, cases    | SQLite3    |
| ChromaDB  | Policy documents (vector search)            | ChromaDB   |

---

## SQLite Tables

### `customers`

| Column         | Type      | Notes                                      |
|----------------|-----------|--------------------------------------------|
| customer_id    | TEXT PK   | UUID                                       |
| name           | TEXT      | Full name                                  |
| email          | TEXT      |                                            |
| province       | TEXT      | Affects tax rules (ON, BC, QC, AB, etc.)   |
| date_of_birth  | DATE      |                                            |
| kyc_status     | TEXT      | verified \| pending \| flagged \| expired  |
| risk_profile   | TEXT      | conservative \| balanced \| growth         |
| created_at     | TIMESTAMP |                                            |

---

### `accounts`

| Column                  | Type      | Notes                                                    |
|-------------------------|-----------|----------------------------------------------------------|
| account_id              | TEXT PK   | UUID                                                     |
| customer_id             | TEXT FK   | → customers                                              |
| account_type            | TEXT      | TFSA \| RRSP \| FHSA \| Cash \| Crypto                  |
| account_number          | TEXT      | Synthetic e.g. WS-0042-RRSP                              |
| status                  | TEXT      | active \| frozen \| restricted \| closed                 |
| freeze_reason           | TEXT      | AML_REVIEW \| KYC_EXPIRED \| FRAUD_HOLD \| null          |
| balance                 | REAL      |                                                          |
| available_balance       | REAL      | May differ from balance if holds exist                   |
| currency                | TEXT      | CAD \| USD                                               |
| rrsp_contribution_ytd   | REAL      | Year-to-date RRSP contributions                          |
| tfsa_contribution_ytd   | REAL      | Year-to-date TFSA contributions                          |
| created_at              | TIMESTAMP |                                                          |

---

### `transactions`

| Column           | Type      | Notes                                                                              |
|------------------|-----------|------------------------------------------------------------------------------------|
| transaction_id   | TEXT PK   | UUID                                                                               |
| account_id       | TEXT FK   | → accounts                                                                         |
| transaction_type | TEXT      | deposit \| withdrawal \| wire_in \| wire_out \| transfer_in \| transfer_out \| trade_buy \| trade_sell \| dividend \| drip \| etransfer |
| amount           | REAL      | Always positive; direction implied by type                                         |
| currency         | TEXT      | CAD \| USD                                                                         |
| status           | TEXT      | completed \| pending \| processing \| failed \| reversed \| pending_reversal       |
| description      | TEXT      | Human-readable label                                                               |
| counterparty     | TEXT      | Bank name, person name, or instrument ticker                                       |
| reference_number | TEXT      | Synthetic wire/etransfer reference                                                 |
| failure_reason   | TEXT      | nullable — e.g. INSUFFICIENT_FUNDS, AML_HOLD, RECIPIENT_DECLINED                  |
| initiated_at     | TIMESTAMP |                                                                                    |
| settled_at       | TIMESTAMP | nullable — null if not yet settled                                                 |
| metadata         | JSON      | device_id, ip_country, instrument, quantity, unit_price, login_session_id         |

---

### `login_events`

| Column       | Type      | Notes                              |
|--------------|-----------|------------------------------------|
| event_id     | TEXT PK   | UUID                               |
| customer_id  | TEXT FK   | → customers                        |
| event_type   | TEXT      | login \| logout \| failed_attempt  |
| device_id    | TEXT      |                                    |
| ip_address   | TEXT      | Synthetic                          |
| ip_country   | TEXT      | ISO country code                   |
| user_agent   | TEXT      |                                    |
| occurred_at  | TIMESTAMP |                                    |

---

### `communications`

| Column        | Type      | Notes                                     |
|---------------|-----------|-------------------------------------------|
| comm_id       | TEXT PK   | UUID                                      |
| customer_id   | TEXT FK   | → customers                               |
| direction     | TEXT      | inbound \| outbound                       |
| channel       | TEXT      | email \| sms \| push                      |
| subject       | TEXT      |                                           |
| body_summary  | TEXT      | Short summary (not full body)             |
| sent_at       | TIMESTAMP |                                           |

---

### `cases` — Historical Resolved Cases (ML similarity)

| Column                   | Type      | Notes                                                                         |
|--------------------------|-----------|-------------------------------------------------------------------------------|
| case_id                  | TEXT PK   | UUID                                                                          |
| customer_id              | TEXT FK   | → customers (anonymised in retrieval)                                         |
| issue_type               | TEXT      | WIRE_DELAY \| ACCOUNT_FROZEN \| RRSP_OVER \| TAX_SLIP \| UNAUTH_TRADE \| ETRANSFER_FAIL \| KYC_EXPIRED |
| issue_description        | TEXT      | Free text summary                                                             |
| investigation_steps      | JSON      | Ordered list: [{tool, args, finding}]                                         |
| root_cause               | TEXT      |                                                                               |
| resolution               | TEXT      |                                                                               |
| resolution_type          | TEXT      | AUTO_RESOLVED \| ESCALATED \| REFUNDED \| CORRECTED                          |
| confidence_score         | REAL      | 0.0–1.0                                                                       |
| time_to_resolve_hours    | REAL      |                                                                               |
| created_at               | TIMESTAMP |                                                                               |
| resolved_at              | TIMESTAMP |                                                                               |

---

### `issues` — Incoming (agent processes these)

| Column       | Type      | Notes                                          |
|--------------|-----------|------------------------------------------------|
| issue_id     | TEXT PK   | UUID                                           |
| customer_id  | TEXT FK   | → customers                                    |
| raw_message  | TEXT      | Free text from customer                        |
| channel      | TEXT      | chat \| email \| phone_transcript              |
| urgency      | TEXT      | low \| medium \| high \| critical              |
| status       | TEXT      | open \| investigating \| resolved \| escalated |
| created_at   | TIMESTAMP |                                                |

---

### `run_traces` — Agent Observability (Control Plane)

| Column           | Type      | Notes                                                     |
|------------------|-----------|-----------------------------------------------------------|
| trace_id         | TEXT PK   | UUID                                                      |
| issue_id         | TEXT FK   | → issues                                                  |
| started_at       | TIMESTAMP |                                                           |
| completed_at     | TIMESTAMP |                                                           |
| status           | TEXT      | running \| completed \| escalated \| failed               |
| tool_calls       | JSON      | [{tool, args_digest, latency_ms, result_summary}]         |
| agent_reasoning  | TEXT      | Chain-of-thought summary                                  |
| structured_output| JSON      | Final resolution output                                   |
| confidence_score | REAL      | 0.0–1.0                                                   |
| policy_flags     | JSON      | [{flag_type, triggered_by, severity}]                     |
| token_count      | INTEGER   |                                                           |
| model            | TEXT      |                                                           |

---

## ChromaDB Collections

### Collection: `policies`

Each document is a markdown file embedded as chunks.

| Document File              | Category            | Key Content                                              |
|----------------------------|---------------------|----------------------------------------------------------|
| wire_transfers.md          | WIRE                | Processing timelines, AML hold triggers, failure codes   |
| rrsp_rules.md              | TAX / CONTRIBUTION  | Annual limits, room calculation, over-contribution rules |
| tfsa_rules.md              | TAX / CONTRIBUTION  | Annual limits, over-contribution penalties               |
| account_security.md        | SECURITY            | Freeze triggers, fraud response, unauthorized access SOP |
| etransfer_policy.md        | PAYMENT             | Failure handling, refund timelines, reversal processing  |
| tax_slips.md               | TAX                 | T5, T5008, DRIP tax treatment, RRSP receipt rules        |
| kyc_compliance.md          | COMPLIANCE          | Verification requirements, expiry, renewal steps         |
| trading_policies.md        | TRADING             | Order types, settlement windows, dispute process         |

Metadata per chunk:
```json
{
  "doc_id": "uuid",
  "source_file": "rrsp_rules.md",
  "category": "TAX",
  "section": "Over-contribution Penalties",
  "effective_date": "2025-01-01"
}
```

### Collection: `case_embeddings`

Historical cases embedded for semantic similarity search.

Each case embedded as:
```
Issue: {issue_description}
Root cause: {root_cause}
Resolution: {resolution}
```

---

## Agent Tool Definitions

```python
account.lookup(customer_id)                        # → account records
account.login_history(customer_id, days=30)        # → login_events
account.communication_history(customer_id)         # → communications

transactions.search(account_id, type=None,         # → filtered transactions
                    status=None, days=90)
transactions.metadata(transaction_id)              # → full metadata JSON

policy.search(query, category=None, top_k=3)       # → ChromaDB semantic search

cases.similar(issue_description, top_k=3)          # → case_embeddings similarity

customer.lookup(customer_id)                       # → customer record
```

---

## Entity Relationships

```
customers
  └── accounts (1:N)
        └── transactions (1:N)
  └── login_events (1:N)
  └── communications (1:N)
  └── cases (1:N)
  └── issues (1:N)
        └── run_traces (1:1)
```

---

## Data Volume for Demo

| Table           | Records |
|-----------------|---------|
| customers       | 10      |
| accounts        | 25      |
| transactions    | 800–1000|
| login_events    | 200     |
| communications  | 60      |
| cases           | 80      |
| issues          | 6       |
| policy docs     | 8 files |
