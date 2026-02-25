# Account Security Policy
# Effective Date: 2025-01-01 | Category: SECURITY | Source: Internal Security Operations

---

## 1. Account Freeze Triggers

Accounts may be frozen or restricted under the following conditions:

| Freeze Reason       | Trigger                                                             | Account Status  |
|---------------------|---------------------------------------------------------------------|-----------------|
| AML_REVIEW          | Large transaction or high-risk pattern flagged by compliance system | RESTRICTED      |
| KYC_EXPIRED         | Customer identity verification past renewal deadline               | FROZEN          |
| FRAUD_HOLD          | Suspected unauthorized access or fraudulent activity               | FROZEN          |
| COMPLIANCE_BLOCK    | Regulatory or sanctions screening match                            | FROZEN          |
| CUSTOMER_REQUEST    | Customer-initiated lock (e.g. lost device)                         | RESTRICTED      |
| LEGAL_HOLD          | Court order or regulatory direction                                | FROZEN          |

### Difference Between RESTRICTED and FROZEN
- **RESTRICTED**: Customer can view account but cannot initiate transactions
- **FROZEN**: Full access suspended — no logins processed, no transactions, no data changes

---

## 2. Unauthorized Access Detection Signals

The following signals are used to detect potential unauthorized account access:

### High-Severity Signals (any one triggers mandatory review)
- Login from a country never previously used by the account holder
- Login from an unrecognized device (device_id not in customer's device history)
- Login at unusual hours (between 11 PM and 5 AM local time) combined with immediate transaction
- Multiple failed login attempts followed by a successful login
- Password reset initiated from a new device within 2 hours of login

### Medium-Severity Signals (two or more trigger review)
- Login from a new city within Canada not previously seen
- Login from a new IP address range
- Transaction amount significantly above the customer's 90-day average
- Trade or withdrawal initiated within 5 minutes of login

### Signal Correlation Rule
If any High-Severity signal is present AND a transaction occurred within 2 hours of that login,
the incident is classified as SUSPECTED_FRAUD and triggers mandatory escalation.

---

## 3. Fraud Response Protocol

### Mandatory Escalation — Do Not Auto-Resolve
Any case involving suspected unauthorized access or unauthorized transactions MUST be escalated
to the Security Operations team. Agents are NOT authorized to resolve fraud cases autonomously,
regardless of confidence level.

### Immediate Actions on Fraud Suspicion
1. Flag the run_trace with policy_flag: FRAUD_SUSPECTED
2. Set escalation_priority: CRITICAL
3. Recommend FRAUD_HOLD on the account
4. Do NOT communicate investigation details to the customer (avoid tipping off bad actors)
5. Draft customer communication: "We have identified unusual activity on your account and are
   reviewing it. A member of our team will contact you within 2 hours."

### Security Team SLAs
- Critical (FRAUD_HOLD active): first response within 30 minutes
- High (FRAUD_SUSPECTED, no hold): first response within 2 hours
- Medium (anomalous signals, no transaction): first response within 4 hours

---

## 4. Unauthorized Transaction Dispute Process

### Customer Dispute Window
- Customers must report unauthorized transactions within 60 days of the transaction date
- Transactions reported after 60 days are reviewed on a case-by-case basis

### Investigation Steps (Security Team, not automated)
1. Verify account access logs for the disputed transaction period
2. Compare device fingerprint and IP to customer's known history
3. Review transaction pattern against customer's historical behavior
4. If confirmed unauthorized: initiate reversal and account remediation
5. If inconclusive: escalate to senior security analyst

### Reversal Policy
- Confirmed unauthorized transactions: reversed within 5 business days
- Disputed trades: shares restored or cash equivalent credited pending investigation
- Reversal is not guaranteed and depends on investigation findings

---

## 5. Account Reinstatement After Security Hold

### FRAUD_HOLD Reinstatement
1. Security team completes investigation
2. Customer identity re-verified via video call or in-person (not email)
3. All active sessions terminated
4. New device/password required before access restored
5. Enhanced monitoring applied for 90 days post-reinstatement

### CUSTOMER_REQUEST Lock Reinstatement
- Customer contacts support and confirms identity
- Lock removed after identity verification (government ID required)
- Typical turnaround: same business day

---

## 6. Agent Rules — Security Incidents

| Condition                                          | Required Action                                   |
|----------------------------------------------------|---------------------------------------------------|
| High-severity security signal present              | Mandatory escalation — CRITICAL priority          |
| Unauthorized transaction suspected                 | Mandatory escalation — do not advise or resolve   |
| Customer asks if account was hacked                | Acknowledge concern; do not confirm or deny       |
| Account in FRAUD_HOLD                             | Do not provide account details until hold cleared |
| Customer requests transaction details for dispute  | Provide transaction summary; escalate for action  |

**Security cases must never be auto-resolved. Escalation is mandatory regardless of confidence.**
