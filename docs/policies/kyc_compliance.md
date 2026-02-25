# KYC (Know Your Customer) Compliance Policy
# Effective Date: 2025-01-01 | Category: COMPLIANCE | Source: FINTRAC + Internal Policy

---

## 1. KYC Overview

Wealthsimple is a reporting entity under FINTRAC and is required to verify the identity of all
customers under the Proceeds of Crime (Money Laundering) and Terrorist Financing Act (PCMLTFA).

KYC verification is mandatory:
- At account opening
- At renewal intervals (see Section 3)
- When triggering events occur (see Section 4)

Failure to complete KYC verification results in account restriction or full freeze.

---

## 2. Verification Requirements

### Identity Documents Accepted

| Document Type               | Accepted For           | Notes                                |
|-----------------------------|------------------------|--------------------------------------|
| Canadian Passport           | All account types      | Must be valid (not expired)          |
| Provincial Driver's License | All account types      | Must be valid                        |
| Provincial ID Card          | All account types      | Government-issued                    |
| Permanent Resident Card     | All account types      | Must be valid                        |

### Additional Requirements by Account Type

| Account Type     | Documents Required                                              |
|------------------|-----------------------------------------------------------------|
| Cash / Crypto    | Government-issued photo ID                                      |
| TFSA             | Government-issued photo ID + SIN confirmation                   |
| RRSP             | Government-issued photo ID + SIN confirmation                   |
| FHSA             | Government-issued photo ID + SIN confirmation + residency proof |

### SIN Confirmation
- SIN is confirmed by the last 3 digits (verbally) or by providing a document showing SIN
- Full SIN is never stored by Wealthsimple — only a hash is retained

---

## 3. KYC Renewal Cycle

### Renewal Intervals

| Account Type           | Renewal Interval |
|------------------------|-----------------|
| Cash / Crypto          | 5 years         |
| TFSA                   | 3 years         |
| RRSP                   | 3 years         |
| FHSA                   | 3 years         |
| High-Risk Customers    | 1 year          |

### Renewal Notification Schedule
Wealthsimple sends renewal reminders via email at:
- 90 days before expiry
- 60 days before expiry
- 30 days before expiry
- 14 days before expiry
- On expiry date

### Grace Period and Account Freeze Sequence
- Days 1–7 after expiry: account in WARNING state (transactions allowed, banner displayed)
- Days 8–30 after expiry: account RESTRICTED (view only, no new transactions)
- Day 31+: account FROZEN (full access suspended)

Account freeze due to KYC expiry is a regulatory requirement. It is not punitive and does
not affect the customer's funds — all holdings and balances are preserved.

---

## 4. Triggering Events for Ad-Hoc KYC Review

KYC re-verification may be required outside the normal renewal cycle when:
- Customer changes their legal name
- Customer changes their country of residence
- Account shows signs of high-risk activity (flagged by compliance system)
- Customer is identified on a sanctions list (OFAC, UN, DFATD)
- Customer requests a significant increase in transaction limits

---

## 5. KYC Renewal Process

### Step-by-Step Renewal Instructions

1. **Log in** to the Wealthsimple app or website
2. **Navigate** to Profile → Identity Verification → Renew Verification
3. **Select ID type** from the accepted document list
4. **Upload** a clear photo or scan of the document (front and back for driver's license)
5. **Confirm SIN** (last 3 digits or document upload)
6. **Submit** — review typically completes within 24–48 business hours

### Post-Submission Timeline
- Standard review: 24–48 business hours
- If additional documents requested: customer notified by email within 24 hours
- Account restriction lifted automatically when KYC is approved
- Account freeze lifted within 4 business hours of approval confirmation

### If Renewal is Rejected
- Customer receives email with specific reason for rejection
- Common reasons: blurry document photo, expired ID, name mismatch
- Customer may resubmit immediately with corrected documents
- Three failed attempts trigger manual review by KYC Operations team

---

## 6. Account Access During Freeze

When an account is in FROZEN status due to KYC_EXPIRED:
- Customer cannot log in or access the account
- Scheduled transactions (pre-authorized contributions, auto-invest) are paused
- No fees are charged during the freeze period
- Holdings are not affected — investments remain invested
- Market value fluctuations continue during freeze period
- Customer is not liable for market losses during KYC freeze period

---

## 7. Agent Escalation Rules

| Condition                                                     | Action                                      |
|---------------------------------------------------------------|---------------------------------------------|
| Account frozen for KYC — standard renewal                    | Auto-resolve with renewal instructions      |
| Account frozen for KYC + customer cannot access app          | Escalate — may need alternate submission    |
| Customer requests manual ID verification (video call)         | Escalate to KYC Operations                 |
| KYC rejection after 3 attempts                               | Escalate to KYC Operations                 |
| KYC review pending beyond 48 business hours                  | Escalate to KYC Operations                 |
| Account frozen for COMPLIANCE_BLOCK or LEGAL_HOLD            | Do not discuss reason; escalate immediately |

**KYC_EXPIRED freezes can be resolved by agents with standard renewal instructions.
COMPLIANCE_BLOCK and LEGAL_HOLD freezes must always be escalated — agents must not
provide any information about the reason for these holds.**
