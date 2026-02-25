# Trading Policies
# Effective Date: 2025-01-01 | Category: TRADING | Source: Internal Operations + IIROC

---

## 1. Supported Order Types

| Order Type    | Description                                                              | Availability    |
|---------------|--------------------------------------------------------------------------|-----------------|
| Market Order  | Execute immediately at current market price                              | Market hours    |
| Limit Order   | Execute only at specified price or better                                | Market + after  |
| Stop Order    | Trigger market order when price reaches stop level                      | Market hours    |
| Stop-Limit    | Trigger limit order when stop price is reached                          | Market hours    |

### Market Hours (North American Equities)
- Regular trading: 9:30 AM – 4:00 PM ET, Monday–Friday
- Pre-market: not supported on Wealthsimple
- After-hours: limit orders held and queued for next trading day
- Market is closed on Canadian and US statutory holidays

---

## 2. Settlement

### Settlement Timelines

| Asset Class               | Settlement Period | Notes                                    |
|---------------------------|-------------------|------------------------------------------|
| Canadian equities (TSX)   | T+1               | As of May 2024 (previously T+2)          |
| US equities (NYSE, NASDAQ)| T+1               | As of May 2024                           |
| ETFs                      | T+1               |                                          |
| Mutual funds              | T+1 to T+2        | Depends on fund                          |
| Crypto                    | Near real-time    | Settled on Wealthsimple platform         |
| Cash (USD/CAD conversion) | T+1               |                                          |

### What Settlement Means
- T+1 means the buyer receives securities and the seller receives cash 1 business day after the trade date
- Proceeds from a sale are available in the account on the settlement date (T+1), not the trade date
- Customers attempting to withdraw sale proceeds before settlement may encounter insufficient funds

---

## 3. Fractional Shares

- Wealthsimple supports fractional share purchases for eligible securities
- Fractional shares are not transferable to other brokers (must be sold before transfer)
- Dividend payments on fractional shares are pro-rated
- Fractional shares appear on T5 and T5008 the same as whole shares

---

## 4. Order Cancellation

- Market orders: cannot be cancelled once submitted during market hours
- Limit orders: can be cancelled while pending (before execution)
- Orders are automatically cancelled at end of trading day unless specified as Good-Till-Cancelled (GTC)
- GTC orders expire after 90 calendar days

---

## 5. Unauthorized Trade Dispute Process

### Definition
An unauthorized trade is any transaction executed on a customer's account without their explicit instruction.

### Dispute Window
- Customers must report unauthorized trades within 60 calendar days of the trade date
- Trades reported after 60 days are reviewed on a case-by-case basis only

### How to Report
- Customer contacts support and identifies the specific trade (date, security, amount)
- Agent records the dispute and escalates to Security Operations immediately
- Customer should NOT sell or modify the disputed position during investigation

### Investigation Process (Security Operations)
1. Review login events and access logs for trade session
2. Compare device fingerprint and IP to customer's known history
3. Assess order metadata (timing, size, pattern)
4. If unauthorized confirmed: restore position or credit cash equivalent
5. If account was compromised: full security remediation before reversal

### Resolution Timeline
- Initial response from Security: within 2 business hours of escalation
- Full investigation: 3–5 business days
- Resolution (reversal or denial): within 7 business days of investigation start

### Unauthorized Trade Reversal
- If trade was a SELL: shares restored at cost of executing buy-back, or cash equivalent credited
- If trade was a BUY: position sold and proceeds returned, net of market movement
- Wealthsimple does not guarantee recovery of market losses incurred during the dispute window

---

## 6. Trade Errors (Wealthsimple-Initiated)

If an error in execution is attributable to Wealthsimple platform or system issues:
- Customer is restored to the position they would have held without the error
- Any resulting loss is covered by Wealthsimple
- Customer is notified within 1 business day of error discovery

---

## 7. Wash Trade and Pattern Day Trading

### Pattern Day Trading
- Not restricted on Wealthsimple (no PDT rule for Canadian accounts)
- US accounts held at Wealthsimple may be subject to FINRA PDT rules

### Wash Sale Rules
- Wash sale rules (selling at a loss and rebuying within 30 days) apply to US tax filers
- CRA does not have an equivalent wash sale rule for Canadian tax filers
- Customers with US tax obligations should consult a cross-border tax advisor

---

## 8. Agent Escalation Rules — Trading Issues

| Condition                                                        | Action                                         |
|------------------------------------------------------------------|------------------------------------------------|
| Customer reports unauthorized trade                              | Mandatory escalation to Security — CRITICAL    |
| Customer questions trade execution price                         | Provide trade metadata; escalate if disputed   |
| Customer asks to cancel a completed market order                 | Explain T+1 settlement; cannot reverse         |
| Proceeds not available after T+1 settlement date               | Escalate to Operations                         |
| Customer reports platform error caused missed order             | Escalate to Operations with trade details      |

**Unauthorized trade reports must always be escalated to Security. Agents must not attempt
to investigate, reverse, or resolve unauthorized trade reports autonomously.**
