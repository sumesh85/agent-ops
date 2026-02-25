# Tax Slips Policy
# Effective Date: 2025-01-01 | Category: TAX | Source: CRA + Internal Policy

---

## 1. Tax Slip Types Issued by Wealthsimple

| Slip    | Issued For                                                        | CRA Deadline     |
|---------|-------------------------------------------------------------------|------------------|
| T5      | Investment income: interest, dividends, foreign income            | Last day of Feb  |
| T5008   | Proceeds of disposition (securities sold)                        | Last day of Feb  |
| T4RSP   | RRSP withdrawals and income                                      | Last day of Feb  |
| T4RIF   | RRIF withdrawals and income                                      | Last day of Feb  |
| NR4     | Investment income paid to non-residents                          | Last day of Feb  |
| RRSP Receipt | Contributions for current and prior tax year               | March 31         |

### Threshold for T5 Issuance
- T5 is issued when total investment income from a non-registered account exceeds $50 in the tax year
- If total investment income is below $50, no T5 is issued but income is still taxable
- TFSA income is NOT reported on a T5 (tax-free)
- RRSP income is NOT reported on a T5 (tax-deferred, reported on withdrawal via T4RSP)

---

## 2. T5 — Statement of Investment Income

### Box Definitions

| Box | Description                                          |
|-----|------------------------------------------------------|
| 13  | Interest from Canadian sources                       |
| 24  | Eligible dividends from Canadian corporations        |
| 25  | Taxable amount of eligible dividends (138% of Box 24)|
| 26  | Dividend tax credit for eligible dividends           |
| 10  | Dividends other than eligible (non-eligible)         |
| 11  | Taxable amount of other dividends (115% of Box 10)   |
| 12  | Dividend tax credit for other dividends              |
| 15  | Foreign income (e.g. US stock dividends)             |
| 16  | Foreign tax paid                                     |

### DRIP (Dividend Reinvestment Plan) and T5 Treatment

**DRIP distributions are taxable dividend income and must be included in the T5.**

When a customer receives a DRIP distribution:
- The dividend is paid in the form of additional shares instead of cash
- The customer did not receive cash, but they received taxable income
- CRA requires DRIP dividends to be reported as dividend income in the year received
- Wealthsimple reports DRIP dividends on the T5 in the same boxes as cash dividends
- The fair market value of shares received through DRIP = the dividend amount for tax purposes

### Common T5 Discrepancy: DRIP Not Counted by Customer
Customers frequently report that their T5 shows more dividend income than they received in cash.
This is almost always explained by DRIP reinvestments:

```
Customer's cash dividends:          $X
+ DRIP dividends (shares received): $Y
= Total T5 reportable income:       $X + $Y
```

To verify: sum all `dividend` type transactions + all `drip` type transactions for the tax year.
The total should equal the T5 reported amount.

### ACB (Adjusted Cost Base) and DRIP
- DRIP shares have an ACB equal to the fair market value at the time of reinvestment
- Customers must track DRIP ACB for future capital gains calculations when shares are sold
- Wealthsimple tracks ACB for securities held in Wealthsimple accounts

---

## 3. T5008 — Statement of Securities Transactions

- Issued for each security sold during the tax year
- Reports proceeds of disposition (selling price) NOT capital gains
- Customer must calculate capital gains: Proceeds − ACB − Commissions
- Wealthsimple provides an ACB report to assist with capital gains calculations
- T5008 is informational; CRA cross-references with broker-reported proceeds

---

## 4. RRSP Contribution Receipts

- Two receipts issued per tax year:
  1. **First 60 days receipt**: for contributions made January 1 – March 1 (applicable to prior tax year)
  2. **Remainder of year receipt**: for contributions made March 2 – December 31
- Receipts are available in the Wealthsimple app and sent by mail if requested
- RRSP contributions reduce taxable income in the year claimed (customer chooses when to deduct)

---

## 5. Missing or Incorrect Tax Slips

### Timeline for Slip Issuance
- Tax slips are issued by the last business day of February for the prior tax year
- Slips are available in the Wealthsimple app under Documents before the paper mail deadline
- Amended slips are issued if errors are identified after initial issuance

### If a Customer Reports a Missing Slip
1. Confirm the tax year and account type (TFSA income does not generate a T5)
2. Confirm income exceeds $50 threshold for T5 issuance
3. Verify slip was issued in the Documents section of the app
4. If slip not in app and threshold exceeded: escalate to Operations for slip reissuance

### If a Customer Reports an Incorrect Amount
1. Pull all relevant transactions for the tax year (dividend, drip, interest)
2. Compare sum to T5 reported amount
3. If DRIP transactions account for the difference: explain per Section 2 above
4. If discrepancy remains after DRIP reconciliation: escalate to Finance for T5 amendment

---

## 6. Agent Rules — Tax Slip Issues

| Condition                                               | Action                                      |
|---------------------------------------------------------|---------------------------------------------|
| T5 amount differs from customer's cash dividends only   | Check DRIP — likely explains the difference |
| Slip not issued but income > $50 in taxable account    | Escalate to Operations                      |
| Customer asks how to report income on their return     | Provide box reference; do not advise on tax |
| Customer asks whether to claim RRSP deduction this year| Escalate — this is tax advice               |
| Amended T5 needed                                       | Escalate to Finance team                    |

**Agents must not provide tax filing advice. Explaining what a slip reports is acceptable.
Advising on tax strategy or whether to claim deductions is not.**
