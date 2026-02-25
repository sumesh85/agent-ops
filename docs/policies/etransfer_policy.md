# Interac e-Transfer Policy
# Effective Date: 2025-01-01 | Category: PAYMENT | Source: Internal Operations

---

## 1. e-Transfer Processing Overview

Wealthsimple supports Interac e-Transfer for sending and receiving funds between Canadian bank accounts.

### Sending Limits
- Per transaction: up to $3,000 CAD
- Daily limit: $3,000 CAD
- 30-day limit: $10,000 CAD

### Receiving Limits
- No limit on incoming e-Transfers
- Funds are available upon deposit confirmation (typically within minutes to 4 hours)

### Processing Hours
- e-Transfers can be initiated 24/7
- Processing by Interac network: near real-time for most Canadian financial institutions
- Some receiving institutions may delay deposit until next business day

---

## 2. e-Transfer Failure Codes and Causes

| Failure Code          | Meaning                                                       | Who Resolves              |
|-----------------------|---------------------------------------------------------------|---------------------------|
| RECIPIENT_DECLINED    | Recipient did not accept the transfer within the expiry window| Customer (resend or cancel)|
| RECIPIENT_NOT_FOUND   | Email/phone not registered with Interac                      | Customer to verify contact|
| EXPIRED               | Transfer not accepted within 30 days                         | Auto-cancelled; refunded  |
| LIMIT_EXCEEDED        | Transfer amount exceeds sending limit                        | Customer to split transfer |
| ACCOUNT_RESTRICTED    | Sender account restricted from outbound transfers            | Compliance review required|
| AUTODEPOSIT_FAILED    | Recipient's autodeposit configuration failed at their bank   | Recipient to fix at bank  |
| FRAUD_BLOCK           | Transfer blocked by fraud detection system                   | Escalate to Security      |

---

## 3. Failed e-Transfer Refund Timeline

### Standard Refund Process
- When an e-Transfer fails (any failure code), a reversal is initiated automatically
- The debit from the sender's account is reversed
- Refund timeline depends on failure type:

| Failure Type         | Refund Timeline                                      |
|----------------------|------------------------------------------------------|
| RECIPIENT_DECLINED   | 1–3 business days from decline date                 |
| EXPIRED              | 1–2 business days after 30-day expiry               |
| LIMIT_EXCEEDED       | Same day (transfer never leaves account)            |
| AUTODEPOSIT_FAILED   | 1–3 business days                                   |
| FRAUD_BLOCK          | 3–5 business days (pending security review)         |

### Refund Status States

| Status             | Meaning                                                          |
|--------------------|------------------------------------------------------------------|
| PENDING_REVERSAL   | Refund initiated; awaiting processing by Interac/banking network |
| REVERSED           | Refund completed; funds returned to account                      |

**PENDING_REVERSAL is a normal processing state — it does not indicate a lost or missing refund.**
Customers should wait the full processing window before escalating.

---

## 4. Multiple Failed Transfer Handling

### Same-Day Retry Scenario
If a customer sends two transfers to the same recipient in quick succession and both fail:
- Both are reversed independently
- The second reversal may be batched with overnight processing depending on timing
- Both reversals will complete within 3 business days
- The account available_balance will reflect the pending reversals as holds

### Available Balance vs. Balance
- **Balance**: Total funds in account
- **Available balance**: Balance minus any pending holds or reversals
- During PENDING_REVERSAL, the refund amount is held and will not appear in available_balance
  until the reversal completes

---

## 5. Transfer Expiry Policy

- e-Transfers expire 30 days after being sent if not accepted
- Expired transfers are automatically cancelled and refunded
- Customers should not resend before confirming the original transfer status
- Sending a duplicate transfer before cancellation may result in double payment

---

## 6. Autodeposit

- Recipients can register for Autodeposit through their bank
- Autodeposit transfers are deposited instantly without the recipient needing to accept
- If autodeposit is configured, the sender receives confirmation within minutes
- Autodeposit failures are handled by the recipient's bank — Wealthsimple cannot intervene

---

## 7. Agent Escalation Rules

| Condition                                                        | Action                             |
|------------------------------------------------------------------|------------------------------------|
| Refund in PENDING_REVERSAL within 3 business days               | Auto-resolve with timeline         |
| Refund not received after 3 business days                       | Escalate to Operations             |
| Transfer blocked with FRAUD_BLOCK code                         | Escalate to Security               |
| Customer reports sending to wrong recipient (accepted)          | Escalate — recovery not guaranteed |
| Customer sent duplicate transfer (both accepted)               | Escalate to Operations for review  |
