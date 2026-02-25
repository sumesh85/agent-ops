# Wire Transfer Policy
# Effective Date: 2025-01-01 | Category: WIRE | Source: Internal Operations

---

## 1. Processing Timelines

### Domestic Wire Transfers (CAD, within Canada)
- Standard processing: 1–2 business days after initiation
- Same-day processing: available for wires initiated before 2:00 PM ET on business days
- Wires initiated after 2:00 PM ET are processed the next business day
- Weekend/holiday wires are queued and processed on the next business day

### International Wire Transfers (USD and other currencies)
- Standard processing: 3–5 business days
- Processing time begins when the sending bank releases the funds, not when the customer initiates
- Currency conversion applies for non-CAD wires; exchange rate locked at time of release
- SWIFT transfers may incur intermediary bank delays outside Wealthsimple's control

### Inbound Wires
- Funds are available once the wire clears the receiving bank and passes compliance review
- Compliance review for inbound wires typically completes within 1 business day
- Large inbound wires (see Section 3) may take an additional 1–3 business days for AML review

---

## 2. Wire Failure Codes and Root Causes

| Failure Code          | Meaning                                                      | Resolution Path               |
|-----------------------|--------------------------------------------------------------|-------------------------------|
| INVALID_ACCOUNT       | Destination account number incorrect or closed               | Customer to verify recipient  |
| INSUFFICIENT_FUNDS    | Account balance insufficient at time of processing           | Customer to fund account      |
| AML_HOLD              | Transaction flagged for anti-money laundering review         | Compliance team reviews       |
| BANK_REJECTED         | Receiving bank rejected the wire                             | Customer to contact recipient  |
| INVALID_SWIFT         | SWIFT/routing code incorrect for international wire          | Customer to verify bank codes |
| COMPLIANCE_BLOCK      | Transaction blocked by internal compliance rules             | Escalate to Compliance team   |
| PROCESSING_TIMEOUT    | Wire did not settle within the processing window             | Auto-retried once; then manual|

---

## 3. AML Review Triggers (FINTRAC Compliance)

Wealthsimple is subject to FINTRAC (Financial Transactions and Reports Analysis Centre of Canada) regulations under the Proceeds of Crime (Money Laundering) and Terrorist Financing Act.

### Automatic AML Hold Conditions
- Any single inbound wire transfer of CAD $10,000 or more triggers a Large Transaction review
- Multiple inbound transfers totalling $10,000 or more within a 24-hour period
- Transfers from jurisdictions on FINTRAC's high-risk country list
- Transfers where sender name does not match account holder name
- First-time large wire from a new counterparty institution

### AML Review Timeline
- Standard AML review: 1–3 business days
- Complex cases: up to 5 business days
- If review exceeds 5 business days, customer will be contacted by the Compliance team
- Account may be placed in RESTRICTED status during AML review — this is a regulatory requirement, not an indication of fraud

### Account Status During AML Review
- Account status: RESTRICTED with freeze_reason: AML_REVIEW
- Customer may view existing balances and positions but cannot initiate new transactions
- Restriction is automatically lifted when AML review is completed and cleared
- Customer should NOT be alarmed — AML review is a standard compliance step for large inbound transfers

---

## 4. Escalation Rules for Wire Issues

| Condition                                        | Action                              |
|--------------------------------------------------|-------------------------------------|
| Wire in PROCESSING status beyond 5 business days| Escalate to Operations team         |
| Wire FAILED with AML_HOLD code                  | Escalate to Compliance team         |
| Customer claims wire sent but not received       | Initiate wire trace with sending bank|
| Wire received but account not credited           | Escalate to Finance/Reconciliation  |
| Suspected fraudulent wire instruction            | Immediate escalation to Security    |

---

## 5. Refund and Reversal Policy

- Failed outbound wires are reversed within 1–2 business days
- Reversal timeline begins when the failure is confirmed by the receiving bank
- Refunds for failed inbound wires depend on the sending bank's reversal process (typically 3–5 business days)
- Wealthsimple does not charge fees for failed wire transfers
- International wire fees may not be refunded if failure occurs at an intermediary bank

---

## 6. Customer Communication Standards

- Customers receive email confirmation when a wire is initiated
- Customers receive email notification when a wire is completed or fails
- For wires under AML review, customers receive a notification that funds are "under compliance review" within 1 business day
- Agent responses should NOT disclose specific AML screening criteria to customers
