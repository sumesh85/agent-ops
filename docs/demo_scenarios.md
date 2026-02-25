# Demo Scenarios
# Financial Issue Investigation Agent — AgentOps MVP

---

## Design Principles

Each scenario is chosen to demonstrate a different type of agent reasoning:

- **Cross-system correlation** — findings from separate tools must be combined
- **Policy interpretation** — non-obvious rules that a lookup alone can't answer
- **Calculation under uncertainty** — agent must reason, not just retrieve
- **Hard escalation boundary** — agent must refuse to auto-resolve regardless of confidence
- **Transaction state machine** — multiple states across time must be reconciled
- **Sequential process resolution** — multi-step guidance with clear human handoff

Scenarios are ordered: simple → complex, and auto-resolved → escalated.

---

## Coverage Matrix

| # | Scenario              | Issue Type      | Resolution       | Key Reasoning              | Urgency  |
|---|-----------------------|-----------------|------------------|----------------------------|----------|
| 1 | Wire + Silent Freeze  | WIRE_DELAY      | Auto-resolved    | Cross-system correlation   | High     |
| 2 | RRSP Over-contribution| RRSP_OVER       | Escalate         | Calculation + uncertainty  | Medium   |
| 3 | Unauthorized Trade    | UNAUTH_TRADE    | Critical escalate| Security signal correlation| Critical |
| 4 | T5 vs Actual Dividends| TAX_SLIP        | Auto-resolved    | Policy interpretation      | Medium   |
| 5 | Failed E-Transfer     | ETRANSFER_FAIL  | Auto-resolved    | Transaction state machine  | Medium   |
| 6 | Account Frozen: KYC   | KYC_EXPIRED     | Auto + guided    | Sequential process         | High     |

---

## Scenario 1 — Wire Transfer Delay + Silent Freeze

### Customer Message
> "My $15,000 wire transfer from TD Bank hasn't shown up in 4 business days and my account seems
> partially restricted. I need this money urgently to close on a property purchase."

### Setup (Synthetic Data Required)
- Account status: `restricted`, freeze_reason: `AML_REVIEW`
- Transaction: wire_in, $15,000, status: `processing`, initiated 4 days ago
- 3 historical cases: large wire → AML hold → cleared on day 5

### Investigation Path

| Step | Tool Called                                      | Finding                                              |
|------|--------------------------------------------------|------------------------------------------------------|
| 1    | `account.lookup(customer_id)`                    | Status RESTRICTED, freeze_reason: AML_REVIEW         |
| 2    | `transactions.search(account_id, type=wire_in)`  | $15,000 wire, status: PROCESSING, day 4              |
| 3    | `policy.search("wire AML hold large transfer")`  | Wires >$10,000 trigger 3–5 day AML review per FINTRAC|
| 4    | `cases.similar("large wire AML restriction")`    | 3 similar cases — all cleared automatically on day 5 |

### Structured Output
```json
{
  "issue_type": "WIRE_DELAY",
  "root_cause": "Inbound wire >$10,000 triggered automatic AML review per FINTRAC compliance.",
  "resolution": "Wire is processing normally. AML hold is a regulatory requirement, not a fraud flag. Expected clearance: 1 business day.",
  "resolution_type": "AUTO_RESOLVED",
  "next_steps": [
    "No action required from customer.",
    "Funds expected to be available by end of next business day.",
    "Customer may contact support if funds do not arrive after 6 business days."
  ],
  "confidence_score": 0.87,
  "escalate": false,
  "policy_flags": ["AML_REVIEW_TRIGGERED"]
}
```

### Why This Scenario Works
The freeze and the wire delay appear unrelated from the customer's view. The agent connects them
by correlating two separate tool results — neither alone explains the full picture.

---

## Scenario 2 — RRSP Over-contribution Risk

### Customer Message
> "I just transferred $20,000 into my RRSP but I received a warning email from Wealthsimple.
> Am I going to be penalized by CRA? I'm worried about the 1% monthly penalty."

### Setup (Synthetic Data Required)
- RRSP account: rrsp_contribution_ytd = $29,500 (before the $20,000)
- Transactions: $9,500 RRSP deposit in March + $20,000 deposit today
- Customer profile: province ON, no prior-year NOA data in synthetic DB
- 2025 RRSP limit: $31,560 (CRA published)
- Total contributions: $29,500 — customer is $2,060 under the known limit... but we can't confirm prior-year unused room

### Investigation Path

| Step | Tool Called                                          | Finding                                                     |
|------|------------------------------------------------------|-------------------------------------------------------------|
| 1    | `customer.lookup(customer_id)`                       | Province: ON, no NOA data available                         |
| 2    | `account.lookup(customer_id)` → filter RRSP          | rrsp_contribution_ytd: $29,500                              |
| 3    | `transactions.search(account_id, type=deposit)`      | $9,500 in March + $20,000 today = $29,500 total             |
| 4    | `policy.search("RRSP contribution limit 2025")`      | 2025 limit: $31,560; unused prior room can increase ceiling |
| 5    | `policy.search("RRSP over-contribution penalty CRA")`| 1% per month on excess over $2,000 buffer                   |
| 6    | `cases.similar("RRSP over-contribution warning")`    | Similar case — DRIP miscounted; different root cause         |

### Agent Reasoning Checkpoint
> "Total known contributions: $29,500. 2025 limit: $31,560. Customer appears $2,060 under limit.
> However, I cannot confirm prior-year unused contribution room without Notice of Assessment data.
> If customer has used prior-year room in a previous plan, actual ceiling could be lower.
> Confidence insufficient to auto-resolve. Escalating with full evidence."

### Structured Output
```json
{
  "issue_type": "RRSP_OVER",
  "root_cause": "Cannot confirm: total contributions appear within 2025 limit ($29,500 of $31,560) but prior-year unused room is unknown.",
  "resolution": "Escalating to advisor. Customer may or may not be over-limit depending on prior-year contribution room.",
  "resolution_type": "ESCALATED",
  "evidence_summary": {
    "contributions_ytd": 29500,
    "known_2025_limit": 31560,
    "apparent_headroom": 2060,
    "prior_year_room_confirmed": false
  },
  "next_steps": [
    "Advisor to verify prior-year contribution room via NOA.",
    "If over-limit: advise on withdrawal options to avoid penalty.",
    "Do not advise customer on tax matters until advisor review."
  ],
  "confidence_score": 0.54,
  "escalate": true,
  "policy_flags": ["TAX_ADVICE_REQUIRED", "CRA_PENALTY_RISK"]
}
```

### Why This Scenario Works
Agent knows what it doesn't know. It explicitly identifies the missing variable (prior-year room)
and refuses to guess on a tax matter. This directly demonstrates the "where AI should not decide"
principle from the brief.

---

## Scenario 3 — Suspected Unauthorized Trade

### Customer Message
> "I just checked my account and there's a sell order on my Apple shares for $8,400 that I never
> placed. I did not make this trade. Someone may have gotten into my account."

### Setup (Synthetic Data Required)
- Trade: AAPL sell, $8,400, initiated at 02:14 AM, settled
- Login event: 90 min before trade, IP country: Romania, unknown device_id
- Customer's normal login history: all Canada, same 2 devices
- 2 historical fraud cases with identical pattern (night login, foreign IP, immediate trade)

### Investigation Path

| Step | Tool Called                                              | Finding                                              |
|------|----------------------------------------------------------|------------------------------------------------------|
| 1    | `account.lookup(customer_id)`                            | Status: active (no freeze yet)                       |
| 2    | `transactions.search(account_id, type=trade_sell)`       | AAPL sell $8,400, initiated 02:14 AM                 |
| 3    | `transactions.metadata(transaction_id)`                  | device_id: unknown, ip_country: RO                   |
| 4    | `account.login_history(customer_id, days=30)`            | Login from Romania 90 min before trade; never before |
| 5    | `policy.search("unauthorized trade fraud account freeze")`| Mandatory escalation + immediate freeze required     |
| 6    | `cases.similar("foreign login unauthorized trade")`      | 2 confirmed fraud cases, identical pattern           |

### Hard Policy Boundary
Agent hits a policy rule: unauthorized transaction suspicion → mandatory escalation regardless of
confidence score. Agent does NOT attempt to auto-resolve even at 96% confidence.

### Structured Output
```json
{
  "issue_type": "UNAUTH_TRADE",
  "root_cause": "High-confidence unauthorized access. Foreign login (Romania) from unknown device 90 minutes before $8,400 trade. Pattern matches 2 confirmed fraud cases.",
  "resolution": "Immediate escalation to Security team. Account freeze recommended pending investigation.",
  "resolution_type": "ESCALATED",
  "security_signals": [
    {"signal": "foreign_ip", "value": "RO", "severity": "HIGH"},
    {"signal": "unknown_device", "severity": "HIGH"},
    {"signal": "off_hours_trade", "value": "02:14 AM", "severity": "MEDIUM"},
    {"signal": "case_similarity", "value": "2 confirmed fraud matches", "severity": "HIGH"}
  ],
  "confidence_score": 0.96,
  "escalate": true,
  "escalation_priority": "CRITICAL",
  "policy_flags": ["FRAUD_SUSPECTED", "MANDATORY_ESCALATION", "ACCOUNT_FREEZE_RECOMMENDED"]
}
```

### Why This Scenario Works
Shows the hard human-in-the-loop boundary. High confidence does not mean auto-resolve when the
policy is clear. The agent surfaces all evidence concisely so the security team can act immediately.

---

## Scenario 4 — T5 Dividend vs. Actual Dividends Mismatch

### Customer Message
> "My T5 slip from Wealthsimple shows $1,200 in dividend income, but when I add up all the
> dividend payments I received in my account, I only get $890. My accountant says I need to
> report the T5 amount but I don't understand the discrepancy."

### Setup (Synthetic Data Required)
- Transactions: $890 in `dividend` type transactions across 2024
- Transactions: $310 in `drip` (dividend reinvestment) type transactions across 2024
- $890 + $310 = $1,200 — matches T5 exactly
- Policy doc: DRIP is taxable dividend income per CRA, must be reported on T5

### Investigation Path

| Step | Tool Called                                              | Finding                        |
|------|----------------------------------------------------------|--------------------------------|
| 1    | `account.lookup(customer_id)`                            | Cash account + TFSA            |
| 2    | `transactions.search(account_id, type=dividend, days=365)` | $890 total cash dividends   |
| 3    | `transactions.search(account_id, type=drip, days=365)`  | $310 DRIP reinvestments        |
| 4    | `policy.search("DRIP dividend reinvestment tax T5")`    | DRIP = taxable dividend income; included in T5 per CRA rules |
| 5    | Calculate                                               | $890 + $310 = $1,200 — matches T5 exactly |

### Structured Output
```json
{
  "issue_type": "TAX_SLIP",
  "root_cause": "Customer's records exclude DRIP (dividend reinvestment) transactions. CRA requires DRIP to be reported as dividend income and Wealthsimple includes it in the T5.",
  "resolution": "T5 amount of $1,200 is correct. Breakdown: $890 cash dividends + $310 DRIP reinvestments = $1,200.",
  "resolution_type": "AUTO_RESOLVED",
  "breakdown": {
    "cash_dividends": 890.00,
    "drip_reinvestments": 310.00,
    "total_reportable": 1200.00,
    "t5_amount": 1200.00,
    "discrepancy": 0.00
  },
  "next_steps": [
    "Customer should report $1,200 on line 12000 of their T1 return.",
    "DRIP shares received are also subject to adjusted cost base tracking for future capital gains.",
    "Customer's accountant can confirm using the transaction history attached."
  ],
  "confidence_score": 0.97,
  "escalate": false,
  "policy_flags": ["TAX_RELATED"]
}
```

### Why This Scenario Works
The gap between what the customer sees (cash dividends) and what's taxable (cash + DRIP) is
bridged entirely by policy reasoning. No rule lookup returns the answer directly — the agent
must combine two transaction types and interpret the policy to explain the discrepancy.

---

## Scenario 5 — Failed E-Transfer + Missing Refund

### Customer Message
> "I tried to send $500 to my friend twice because the first one said it failed. Now both
> transactions show as failed but only one refund came back. I'm missing $500."

### Setup (Synthetic Data Required)
- Transaction 1: etransfer $500, status: `failed`, failure_reason: RECIPIENT_DECLINED, reversed (+$500, completed)
- Transaction 2: etransfer $500, status: `failed`, failure_reason: RECIPIENT_DECLINED, reversal status: `pending_reversal`
- Policy doc: failed e-transfer reversals process in 1–3 business days; second attempt within 24h may batch

### Investigation Path

| Step | Tool Called                                              | Finding                                                  |
|------|----------------------------------------------------------|----------------------------------------------------------|
| 1    | `account.lookup(customer_id)`                            | Active, available balance lower than balance             |
| 2    | `transactions.search(account_id, type=etransfer)`        | Two $500 debits, both FAILED                             |
| 3    | `transactions.search(account_id, status=reversed)`       | One +$500 reversal COMPLETED; one +$500 PENDING_REVERSAL |
| 4    | `policy.search("etransfer failed refund reversal timeline")`| Pending reversals: 1–3 business days                 |
| 5    | `cases.similar("failed etransfer missing refund")`       | 5 identical cases — all resolved when reversal cleared   |

### Structured Output
```json
{
  "issue_type": "ETRANSFER_FAIL",
  "root_cause": "Both e-transfers failed (recipient declined). First refund processed. Second refund is in PENDING_REVERSAL status — this is normal processing, not a missing refund.",
  "resolution": "Second $500 refund is queued and will post within 1–3 business days. No funds are lost.",
  "resolution_type": "AUTO_RESOLVED",
  "transaction_summary": [
    {"tx": "etransfer_1", "amount": -500, "status": "failed", "refund_status": "COMPLETED"},
    {"tx": "etransfer_2", "amount": -500, "status": "failed", "refund_status": "PENDING_REVERSAL"}
  ],
  "next_steps": [
    "No action required. Second refund expected by [date + 3 business days].",
    "If refund does not appear after 3 business days, contact support with reference number."
  ],
  "confidence_score": 0.92,
  "escalate": false,
  "policy_flags": []
}
```

### Why This Scenario Works
The customer sees $500 missing. The agent must reconcile debit, failure, refund, and pending
reversal as a transaction lifecycle — not as independent events. Traditional rule engines require
every state path predefined. The agent infers it from data + policy.

---

## Scenario 6 — Account Fully Frozen: KYC Expired

### Customer Message
> "My Wealthsimple account is completely locked. I can't log in or access any of my money.
> I've had the account for 3 years and nothing like this has happened before. What's going on?"

### Setup (Synthetic Data Required)
- Account status: `frozen`, freeze_reason: `KYC_EXPIRED`
- KYC expired 32 days ago
- Communications: 3 reminder emails sent (days -60, -30, -14), no response logged
- Account types: TFSA + RRSP (requires government ID + SIN confirmation for renewal)
- Policy doc: KYC must be renewed every 3 years for registered accounts; non-response leads to freeze

### Investigation Path

| Step | Tool Called                                              | Finding                                              |
|------|----------------------------------------------------------|------------------------------------------------------|
| 1    | `account.lookup(customer_id)`                            | Status: FROZEN, freeze_reason: KYC_EXPIRED           |
| 2    | `customer.lookup(customer_id)`                           | KYC expired 32 days ago (last verified 3 years prior)|
| 3    | `account.communication_history(customer_id)`            | 3 reminder emails sent; no response recorded         |
| 4    | `policy.search("KYC expiry renewal registered account")` | 3-year renewal cycle; TFSA/RRSP require ID + SIN     |
| 5    | `transactions.search(account_id, days=60)`               | All transactions normal prior to freeze              |

### Structured Output
```json
{
  "issue_type": "KYC_EXPIRED",
  "root_cause": "KYC verification expired after 3-year cycle. Account frozen automatically after 32 days of non-renewal. 3 reminder emails were sent with no response.",
  "resolution": "Account will be unfrozen within 24–48 hours of successful KYC resubmission.",
  "resolution_type": "AUTO_RESOLVED",
  "documents_required": [
    "Government-issued photo ID (passport or driver's license)",
    "SIN confirmation (last 3 digits verbally or document)"
  ],
  "next_steps": [
    "1. Customer visits: wealthsimple.com/kyc-renewal (synthetic link for demo)",
    "2. Upload required documents.",
    "3. Review typically completes within 24–48 hours.",
    "4. Account access restored automatically upon approval."
  ],
  "confidence_score": 0.99,
  "escalate": false,
  "policy_flags": ["KYC_COMPLIANCE", "REGISTERED_ACCOUNT"]
}
```

### Why This Scenario Works
Simple root cause, but the agent must answer several sub-questions in sequence: why is it frozen,
when did it expire, what was communicated, what are the exact steps to resolve. Each step requires
a different tool. The result is a complete, actionable resolution the customer can act on immediately.

---

## Demo Script (3-Minute Flow)

```
[00:00] Open Stability Overview — show 6 runs, mixed confidence scores
[00:30] Click Scenario 4 (T5 Dividends) — simple auto-resolve, show tool trace
[01:00] Click Scenario 3 (Unauthorized Trade) — high confidence, STILL escalated
         → "Notice: agent escalates despite 96% confidence — policy boundary"
[01:45] Click Scenario 2 (RRSP) — agent explicitly states what it doesn't know
         → "This is AI knowing its limits"
[02:15] Show Run Detail for any scenario — audit trail, tool calls, policy flags
[02:45] Close: "Every decision is traceable. Every boundary is enforced."
```

---

## Synthetic Data Generation Order

1. customers (10 records)
2. accounts (2–3 per customer, covering all account types)
3. transactions (150–200 per scenario-linked account; 30–50 for others)
4. login_events (200 records; anomalous ones for Scenario 3)
5. communications (60 records; reminder emails for Scenario 6)
6. cases (80 historical resolved cases for similarity matching)
7. issues (6 records — one per scenario)
8. policy docs (8 markdown files → embed into ChromaDB)
