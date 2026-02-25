#!/usr/bin/env python3
"""
seed_db.py — Synthetic data generator for AgentOps demo.

Idempotent: truncates all tables and rebuilds on every run.
Generates deterministic demo-scenario rows + randomised background data.

Run via:  python scripts/seed_db.py
       or make seed (inside Docker)
"""

import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
from faker import Faker

fake = Faker("en_CA")
rng = random.Random(42)          # seeded → reproducible background data
UTC = timezone.utc


# ── Helpers ──────────────────────────────────────────────────────────────────

def uid() -> str:
    return str(uuid.uuid4())

def now() -> datetime:
    return datetime.now(UTC)

def days_ago(n: float) -> datetime:
    return now() - timedelta(days=n)

def hours_ago(n: float) -> datetime:
    return now() - timedelta(hours=n)

def jd(obj: object) -> str:
    """Serialise to JSON string for asyncpg JSONB columns."""
    return json.dumps(obj, default=str)


# ── Fixed IDs for the 6 demo scenarios (deterministic) ───────────────────────

CUST = {
    "alex":   "cust-alex-chen-0001",        # Scenario 1: Wire + AML
    "sarah":  "cust-sarah-mitchell-0002",   # Scenario 2: RRSP over
    "james":  "cust-james-park-0003",       # Scenario 3: Unauth trade
    "maria":  "cust-maria-santos-0004",     # Scenario 4: T5 mismatch
    "david":  "cust-david-kim-0005",        # Scenario 5: Failed e-transfer
    "emma":   "cust-emma-thompson-0006",    # Scenario 6: KYC expired
}

ACC = {
    "alex_cash":   "acc-alex-cash-0001",
    "sarah_rrsp":  "acc-sarah-rrsp-0002",
    "sarah_tfsa":  "acc-sarah-tfsa-0002b",
    "james_cash":  "acc-james-cash-0003",
    "maria_cash":  "acc-maria-cash-0004",
    "david_cash":  "acc-david-cash-0005",
    "emma_tfsa":   "acc-emma-tfsa-0006",
    "emma_rrsp":   "acc-emma-rrsp-0006b",
}

ISSUE = {
    "s1": "issue-wire-aml-0001",
    "s2": "issue-rrsp-over-0002",
    "s3": "issue-unauth-trade-0003",
    "s4": "issue-t5-mismatch-0004",
    "s5": "issue-etransfer-fail-0005",
    "s6": "issue-kyc-frozen-0006",
}


# ── Connection ────────────────────────────────────────────────────────────────

async def connect() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "agentops"),
        user=os.getenv("POSTGRES_USER", "agentops"),
        password=os.getenv("POSTGRES_PASSWORD", "agentops_dev_secret"),
    )


# ── Truncate ──────────────────────────────────────────────────────────────────

async def truncate(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        TRUNCATE TABLE run_traces, issues, cases, communications,
                       login_events, transactions, accounts, customers
        RESTART IDENTITY CASCADE
    """)
    print("  ✓ tables truncated")


# ── Customers ─────────────────────────────────────────────────────────────────

SCENARIO_CUSTOMERS = [
    dict(
        customer_id=CUST["alex"],
        name="Alex Chen",
        email="alex.chen@example.com",
        province="ON",
        kyc_status="verified",
        kyc_verified_at=days_ago(180),
        kyc_expires_at=days_ago(-900),   # expires in 900 days
        risk_profile="balanced",
        created_at=days_ago(540),
    ),
    dict(
        customer_id=CUST["sarah"],
        name="Sarah Mitchell",
        email="sarah.mitchell@example.com",
        province="BC",
        kyc_status="verified",
        kyc_verified_at=days_ago(90),
        kyc_expires_at=days_ago(-1000),
        risk_profile="growth",
        created_at=days_ago(730),
    ),
    dict(
        customer_id=CUST["james"],
        name="James Park",
        email="james.park@example.com",
        province="ON",
        kyc_status="verified",
        kyc_verified_at=days_ago(60),
        kyc_expires_at=days_ago(-1040),
        risk_profile="growth",
        created_at=days_ago(400),
    ),
    dict(
        customer_id=CUST["maria"],
        name="Maria Santos",
        email="maria.santos@example.com",
        province="QC",
        kyc_status="verified",
        kyc_verified_at=days_ago(120),
        kyc_expires_at=days_ago(-980),
        risk_profile="conservative",
        created_at=days_ago(900),
    ),
    dict(
        customer_id=CUST["david"],
        name="David Kim",
        email="david.kim@example.com",
        province="AB",
        kyc_status="verified",
        kyc_verified_at=days_ago(200),
        kyc_expires_at=days_ago(-900),
        risk_profile="balanced",
        created_at=days_ago(300),
    ),
    dict(
        customer_id=CUST["emma"],
        name="Emma Thompson",
        email="emma.thompson@example.com",
        province="ON",
        kyc_status="expired",
        kyc_verified_at=days_ago(365 * 3 + 32),   # verified 3 years + 32 days ago
        kyc_expires_at=days_ago(32),               # expired 32 days ago
        risk_profile="conservative",
        created_at=days_ago(365 * 3 + 60),
    ),
]


async def seed_customers(conn: asyncpg.Connection) -> None:
    rows = []

    # 6 demo customers
    for c in SCENARIO_CUSTOMERS:
        rows.append((
            c["customer_id"], c["name"], c["email"], c["province"],
            fake.date_of_birth(minimum_age=25, maximum_age=65),
            c["kyc_status"], c["kyc_verified_at"], c["kyc_expires_at"],
            c["risk_profile"], c["created_at"],
        ))

    # 4 background customers
    for _ in range(4):
        verified_at = days_ago(rng.randint(30, 500))
        rows.append((
            uid(), fake.name(), fake.email(), rng.choice(["ON", "BC", "AB", "QC", "MB"]),
            fake.date_of_birth(minimum_age=25, maximum_age=65),
            "verified", verified_at, verified_at + timedelta(days=1095),
            rng.choice(["conservative", "balanced", "growth"]),
            days_ago(rng.randint(100, 900)),
        ))

    await conn.executemany("""
        INSERT INTO customers
            (customer_id, name, email, province, date_of_birth,
             kyc_status, kyc_verified_at, kyc_expires_at, risk_profile, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
    """, rows)
    print(f"  ✓ {len(rows)} customers")


# ── Accounts ──────────────────────────────────────────────────────────────────

async def seed_accounts(conn: asyncpg.Connection, bg_customers: list[str]) -> None:
    rows = []

    # ── Scenario 1: Alex — Cash RESTRICTED (AML_REVIEW)
    rows.append((
        ACC["alex_cash"], CUST["alex"], "Cash", "WS-0001-CASH",
        "restricted", "AML_REVIEW",
        48_200.00, 48_200.00, "CAD", 0, 0,
        days_ago(540),
    ))

    # ── Scenario 2: Sarah — RRSP + TFSA (over-contribution risk)
    rows.append((
        ACC["sarah_rrsp"], CUST["sarah"], "RRSP", "WS-0002-RRSP",
        "active", None,
        95_500.00, 95_500.00, "CAD", 29_500.00, 0,
        days_ago(730),
    ))
    rows.append((
        ACC["sarah_tfsa"], CUST["sarah"], "TFSA", "WS-0002-TFSA",
        "active", None,
        22_000.00, 22_000.00, "CAD", 0, 7_000.00,
        days_ago(700),
    ))

    # ── Scenario 3: James — Cash (active; fraud signals in login/tx metadata)
    rows.append((
        ACC["james_cash"], CUST["james"], "Cash", "WS-0003-CASH",
        "active", None,
        31_600.00, 23_200.00, "CAD", 0, 0,
        days_ago(400),
    ))

    # ── Scenario 4: Maria — Cash (dividend + DRIP mismatch)
    rows.append((
        ACC["maria_cash"], CUST["maria"], "Cash", "WS-0004-CASH",
        "active", None,
        54_300.00, 54_300.00, "CAD", 0, 0,
        days_ago(900),
    ))

    # ── Scenario 5: David — Cash (failed e-transfers + missing refund)
    rows.append((
        ACC["david_cash"], CUST["david"], "Cash", "WS-0005-CASH",
        "active", None,
        8_750.00, 7_750.00, "CAD", 0, 0,   # available_balance = balance - pending hold
        days_ago(300),
    ))

    # ── Scenario 6: Emma — TFSA + RRSP both FROZEN (KYC_EXPIRED)
    rows.append((
        ACC["emma_tfsa"], CUST["emma"], "TFSA", "WS-0006-TFSA",
        "frozen", "KYC_EXPIRED",
        41_000.00, 41_000.00, "CAD", 0, 7_000.00,
        days_ago(365 * 3 + 60),
    ))
    rows.append((
        ACC["emma_rrsp"], CUST["emma"], "RRSP", "WS-0006-RRSP",
        "frozen", "KYC_EXPIRED",
        88_500.00, 88_500.00, "CAD", 0, 0,
        days_ago(365 * 3 + 60),
    ))

    # ── Background accounts
    for cid in bg_customers:
        for acct_type in rng.sample(["Cash", "TFSA", "RRSP"], k=rng.randint(1, 2)):
            bal = round(rng.uniform(2000, 80000), 2)
            rows.append((
                uid(), cid, acct_type, f"WS-{uid()[:8].upper()}",
                "active", None, bal, bal, "CAD", 0, 0,
                days_ago(rng.randint(100, 800)),
            ))

    await conn.executemany("""
        INSERT INTO accounts
            (account_id, customer_id, account_type, account_number,
             status, freeze_reason, balance, available_balance, currency,
             rrsp_contribution_ytd, tfsa_contribution_ytd, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
    """, rows)
    print(f"  ✓ {len(rows)} accounts")


# ── Transactions ──────────────────────────────────────────────────────────────

async def seed_transactions(conn: asyncpg.Connection, bg_account_ids: list[str]) -> None:
    rows = []

    # ── S1: Alex — inbound wire PROCESSING (4 days ago), AML hold
    rows.append((
        uid(), ACC["alex_cash"], "wire_in", 15_000.00, "CAD",
        "processing", "Inbound wire — TD Bank", "TD Canada Trust",
        f"WR-{uid()[:10].upper()}", None,
        days_ago(4), None,
        jd({"aml_review": True, "sender_institution": "TD Canada Trust",
             "sender_name": "Alex Chen"}),
    ))
    # Plus some normal history
    for i in range(8):
        rows.append((
            uid(), ACC["alex_cash"], "deposit", round(rng.uniform(500, 3000), 2),
            "CAD", "completed", "Payroll deposit", "Employer",
            f"DEP-{uid()[:8]}", None,
            days_ago(rng.randint(10, 400)), days_ago(rng.randint(5, 9)),
            jd({}),
        ))

    # ── S2: Sarah — RRSP contributions (9,500 in March + 20,000 today)
    rows.append((
        uid(), ACC["sarah_rrsp"], "deposit", 9_500.00, "CAD",
        "completed", "RRSP contribution", "Sarah Mitchell",
        f"RRSP-{uid()[:8]}", None,
        days_ago(310), days_ago(309),   # ~March
        jd({"contribution_type": "rrsp"}),
    ))
    rows.append((
        uid(), ACC["sarah_rrsp"], "deposit", 20_000.00, "CAD",
        "completed", "RRSP contribution", "Sarah Mitchell",
        f"RRSP-{uid()[:8]}", None,
        hours_ago(3), hours_ago(2),
        jd({"contribution_type": "rrsp"}),
    ))
    # TFSA contributions
    rows.append((
        uid(), ACC["sarah_tfsa"], "deposit", 7_000.00, "CAD",
        "completed", "TFSA contribution", "Sarah Mitchell",
        f"TFSA-{uid()[:8]}", None,
        days_ago(60), days_ago(59),
        jd({"contribution_type": "tfsa"}),
    ))

    # ── S3: James — unauthorized AAPL sell at 02:14 AM, foreign login metadata
    fraudulent_session = uid()
    rows.append((
        uid(), ACC["james_cash"], "trade_sell", 8_400.00, "CAD",
        "completed", "AAPL sell — 56 shares @ $150.00", "AAPL",
        f"TRD-{uid()[:8]}", None,
        days_ago(1) - timedelta(hours=21, minutes=46),   # 02:14 AM yesterday
        days_ago(0),
        jd({
            "instrument": "AAPL",
            "quantity": 56,
            "unit_price": 150.00,
            "device_id": "device-unknown-foreign-001",
            "ip_country": "RO",
            "login_session_id": fraudulent_session,
        }),
    ))
    # Normal trading history (legitimate)
    for _ in range(6):
        rows.append((
            uid(), ACC["james_cash"],
            rng.choice(["trade_buy", "trade_sell"]),
            round(rng.uniform(1000, 5000), 2), "CAD",
            "completed", f"{rng.choice(['AAPL','GOOG','MSFT'])} trade", "Market",
            f"TRD-{uid()[:8]}", None,
            days_ago(rng.randint(5, 200)), days_ago(rng.randint(1, 4)),
            jd({
                "device_id": "device-james-iphone-001",
                "ip_country": "CA",
                "login_session_id": uid(),
            }),
        ))

    # ── S4: Maria — cash dividends ($890) + DRIP ($310) → T5 shows $1,200
    for ticker, amount, tx_type in [
        ("RY.TO",  220.00, "dividend"),
        ("TD.TO",  190.00, "dividend"),
        ("ENB.TO", 480.00, "dividend"),
        ("RY.TO",  130.00, "drip"),
        ("TD.TO",   95.00, "drip"),
        ("ENB.TO",  85.00, "drip"),
    ]:
        rows.append((
            uid(), ACC["maria_cash"], tx_type,
            amount, "CAD", "completed",
            f"{ticker} {'dividend' if tx_type == 'dividend' else 'DRIP reinvestment'}",
            ticker, f"DIV-{uid()[:8]}", None,
            days_ago(rng.randint(30, 300)), days_ago(rng.randint(1, 29)),
            jd({"instrument": ticker, "tax_year": 2024, "is_drip": tx_type == "drip"}),
        ))

    # ── S5: David — 2x $500 e-transfer FAILED; one REVERSED, one PENDING_REVERSAL
    etx1 = uid()
    etx2 = uid()
    rows.append((
        etx1, ACC["david_cash"], "etransfer", 500.00, "CAD",
        "failed", "E-Transfer to Mike Wilson", "mike.wilson@example.com",
        f"ET-{uid()[:8]}", "RECIPIENT_DECLINED",
        days_ago(3), None,
        jd({"recipient_email": "mike.wilson@example.com", "attempt": 1}),
    ))
    rows.append((
        etx2, ACC["david_cash"], "etransfer", 500.00, "CAD",
        "failed", "E-Transfer to Mike Wilson (retry)", "mike.wilson@example.com",
        f"ET-{uid()[:8]}", "RECIPIENT_DECLINED",
        days_ago(3) + timedelta(minutes=20), None,
        jd({"recipient_email": "mike.wilson@example.com", "attempt": 2}),
    ))
    # First refund completed
    rows.append((
        uid(), ACC["david_cash"], "etransfer", 500.00, "CAD",
        "reversed", "Reversal: failed e-transfer", None,
        f"REV-{uid()[:8]}", None,
        days_ago(2), days_ago(1),
        jd({"reversal_of": etx1}),
    ))
    # Second refund still pending
    rows.append((
        uid(), ACC["david_cash"], "etransfer", 500.00, "CAD",
        "pending_reversal", "Reversal: failed e-transfer (processing)", None,
        f"REV-{uid()[:8]}", None,
        days_ago(1), None,
        jd({"reversal_of": etx2}),
    ))
    # Normal history
    for _ in range(5):
        rows.append((
            uid(), ACC["david_cash"], "deposit",
            round(rng.uniform(500, 2000), 2), "CAD",
            "completed", "Payroll deposit", "Employer",
            f"DEP-{uid()[:8]}", None,
            days_ago(rng.randint(15, 200)), days_ago(rng.randint(1, 14)),
            jd({}),
        ))

    # ── S6: Emma — normal history before KYC freeze; nothing recent
    for _ in range(10):
        rows.append((
            uid(), ACC["emma_tfsa"],
            rng.choice(["deposit", "withdrawal"]),
            round(rng.uniform(200, 5000), 2), "CAD",
            "completed", "TFSA transaction", None,
            f"TX-{uid()[:8]}", None,
            days_ago(rng.randint(40, 365)), days_ago(rng.randint(38, 364)),
            jd({}),
        ))

    # ── Background transactions
    for acct_id in bg_account_ids:
        for _ in range(rng.randint(15, 35)):
            tx_type = rng.choice(["deposit", "withdrawal", "trade_buy", "trade_sell"])
            rows.append((
                uid(), acct_id, tx_type,
                round(rng.uniform(100, 10000), 2), "CAD",
                "completed", fake.sentence(nb_words=4), None,
                f"TX-{uid()[:8]}", None,
                days_ago(rng.randint(1, 540)), days_ago(rng.randint(0, 1)),
                jd({}),
            ))

    await conn.executemany("""
        INSERT INTO transactions
            (transaction_id, account_id, transaction_type, amount, currency,
             status, description, counterparty, reference_number, failure_reason,
             initiated_at, settled_at, metadata)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
    """, rows)
    print(f"  ✓ {len(rows)} transactions")


# ── Login Events ──────────────────────────────────────────────────────────────

async def seed_login_events(conn: asyncpg.Connection) -> None:
    rows = []

    # ── S3: James — anomalous Romanian login 90 min before the trade
    rows.append((
        uid(), CUST["james"], "login",
        "device-unknown-foreign-001",
        "185.234.219.42", "RO",
        "Mozilla/5.0 (X11; Linux x86_64)",
        days_ago(1) - timedelta(hours=23, minutes=16),   # 00:44 AM — 90 min before trade
    ))
    # James's normal logins from Canada
    for _ in range(12):
        rows.append((
            uid(), CUST["james"], "login",
            rng.choice(["device-james-iphone-001", "device-james-macbook-001"]),
            f"142.{rng.randint(1,254)}.{rng.randint(1,254)}.{rng.randint(1,254)}",
            "CA", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
            days_ago(rng.randint(2, 180)),
        ))

    # Normal logins for other demo customers
    for cid in [CUST["alex"], CUST["sarah"], CUST["maria"], CUST["david"]]:
        for _ in range(rng.randint(5, 15)):
            rows.append((
                uid(), cid, "login",
                f"device-{cid[-4:]}-{rng.choice(['mobile', 'desktop'])}",
                f"99.{rng.randint(1,254)}.{rng.randint(1,254)}.{rng.randint(1,254)}",
                "CA", "Mozilla/5.0",
                days_ago(rng.randint(1, 120)),
            ))

    await conn.executemany("""
        INSERT INTO login_events
            (event_id, customer_id, event_type, device_id, ip_address,
             ip_country, user_agent, occurred_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
    """, rows)
    print(f"  ✓ {len(rows)} login events")


# ── Communications ────────────────────────────────────────────────────────────

async def seed_communications(conn: asyncpg.Connection) -> None:
    rows = []

    # ── S6: Emma — 3 KYC renewal reminders (90, 30, 14 days before expiry)
    for days_before, subject in [
        (90, "Action Required: Your Wealthsimple identity verification expires in 90 days"),
        (30, "Reminder: Renew your identity verification — 30 days remaining"),
        (14, "Urgent: Identity verification expiring in 14 days — account access at risk"),
    ]:
        rows.append((
            uid(), CUST["emma"], "outbound", "email", subject,
            f"KYC renewal reminder sent {days_before} days before expiry. "
            f"Customer instructed to upload government ID and SIN confirmation.",
            days_ago(32 + days_before),   # 32 days ago Emma's KYC expired
        ))
    # On-expiry email
    rows.append((
        uid(), CUST["emma"], "outbound", "email",
        "Your identity verification has expired — account access restricted",
        "KYC expiry notification sent on expiry date. Account moved to RESTRICTED.",
        days_ago(32),
    ))

    # Generic comms for other customers
    for cid in [CUST["alex"], CUST["sarah"], CUST["james"], CUST["maria"], CUST["david"]]:
        for _ in range(rng.randint(2, 5)):
            rows.append((
                uid(), cid, "outbound", rng.choice(["email", "push"]),
                rng.choice([
                    "Monthly statement available",
                    "Trade confirmation",
                    "RRSP contribution receipt",
                    "TFSA contribution confirmation",
                ]),
                "Routine notification", days_ago(rng.randint(1, 200)),
            ))

    await conn.executemany("""
        INSERT INTO communications
            (comm_id, customer_id, direction, channel, subject, body_summary, sent_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
    """, rows)
    print(f"  ✓ {len(rows)} communications")


# ── Historical Cases (for ChromaDB similarity seeding) ───────────────────────

CASE_TEMPLATES = [
    # WIRE_DELAY cases (auto-resolved)
    dict(
        issue_type="WIRE_DELAY",
        issue_description="Customer wire transfer delayed due to AML review on large inbound wire.",
        root_cause="Inbound wire over $10,000 triggered automatic FINTRAC AML review.",
        resolution="Wire cleared automatically after AML review completed on day 5.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.91,
        time_to_resolve_hours=2.5,
    ),
    dict(
        issue_type="WIRE_DELAY",
        issue_description="International wire from US bank taking longer than expected.",
        root_cause="SWIFT intermediary bank delay outside Wealthsimple control.",
        resolution="Wire received on business day 6. Customer notified.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.85,
        time_to_resolve_hours=1.2,
    ),
    dict(
        issue_type="WIRE_DELAY",
        issue_description="Large inbound wire $22,000 account restricted pending review.",
        root_cause="AML hold triggered on wire exceeding $10,000 FINTRAC threshold.",
        resolution="Account restriction lifted automatically after 3-day AML review.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.93,
        time_to_resolve_hours=1.8,
    ),
    # ETRANSFER_FAIL cases
    dict(
        issue_type="ETRANSFER_FAIL",
        issue_description="E-transfer failed, customer says refund hasn't arrived.",
        root_cause="Recipient declined transfer. Reversal in PENDING_REVERSAL status.",
        resolution="Explained reversal timeline (1-3 business days). Refund cleared next day.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.95,
        time_to_resolve_hours=0.5,
    ),
    dict(
        issue_type="ETRANSFER_FAIL",
        issue_description="Two failed e-transfers, only one refund received.",
        root_cause="Second reversal batched to next business day processing cycle.",
        resolution="Second refund confirmed in PENDING_REVERSAL. Cleared within 2 days.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.92,
        time_to_resolve_hours=0.8,
    ),
    dict(
        issue_type="ETRANSFER_FAIL",
        issue_description="E-transfer failed to wrong recipient, money taken from account.",
        root_cause="Recipient email not registered for Interac e-Transfer.",
        resolution="Transfer expired after 30 days, auto-reversed. Customer notified.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.88,
        time_to_resolve_hours=1.5,
    ),
    # TAX_SLIP cases
    dict(
        issue_type="TAX_SLIP",
        issue_description="T5 shows higher dividend income than cash received in account.",
        root_cause="DRIP (dividend reinvestment) distributions included in T5 per CRA rules.",
        resolution="Explained DRIP tax treatment. Cash dividends + DRIP = T5 total.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.97,
        time_to_resolve_hours=0.3,
    ),
    dict(
        issue_type="TAX_SLIP",
        issue_description="Missing T5 slip for investment account.",
        root_cause="Total investment income below $50 CRA reporting threshold.",
        resolution="Confirmed income below $50 threshold; no T5 required but income still taxable.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.99,
        time_to_resolve_hours=0.2,
    ),
    dict(
        issue_type="TAX_SLIP",
        issue_description="T5 amount does not match customer's own records.",
        root_cause="Customer excluded DRIP reinvestment dividends from their manual count.",
        resolution="Provided full transaction breakdown. DRIP + cash dividends matched T5.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.96,
        time_to_resolve_hours=0.4,
    ),
    # RRSP_OVER cases (escalated)
    dict(
        issue_type="RRSP_OVER",
        issue_description="Customer received CRA over-contribution warning after RRSP deposit.",
        root_cause="Customer had RRSP accounts at two institutions; total exceeded limit.",
        resolution="Escalated to tax advisor. Customer withdrew excess via T1-OVP process.",
        resolution_type="ESCALATED",
        confidence_score=0.61,
        time_to_resolve_hours=24.0,
    ),
    dict(
        issue_type="RRSP_OVER",
        issue_description="RRSP contribution warning — prior year unused room unclear.",
        root_cause="NOA not available to confirm prior year contribution room.",
        resolution="Escalated to advisor. Customer confirmed room via CRA My Account.",
        resolution_type="ESCALATED",
        confidence_score=0.55,
        time_to_resolve_hours=18.0,
    ),
    # UNAUTH_TRADE cases (critical escalation)
    dict(
        issue_type="UNAUTH_TRADE",
        issue_description="Customer disputes sell trade made at 1 AM from unknown device.",
        root_cause="Confirmed unauthorized access from Eastern Europe IP. Account compromised.",
        resolution="Security team froze account. Trade reversed. New credentials issued.",
        resolution_type="ESCALATED",
        confidence_score=0.97,
        time_to_resolve_hours=3.0,
    ),
    dict(
        issue_type="UNAUTH_TRADE",
        issue_description="Unauthorized large buy order on customer account overnight.",
        root_cause="Phishing attack — customer credentials obtained. Foreign login confirmed.",
        resolution="Account frozen, unauthorized trade reversed, customer re-verified.",
        resolution_type="ESCALATED",
        confidence_score=0.95,
        time_to_resolve_hours=4.5,
    ),
    # KYC_EXPIRED cases
    dict(
        issue_type="KYC_EXPIRED",
        issue_description="Account fully locked, customer cannot access funds.",
        root_cause="KYC verification expired after 3-year cycle. Renewal not completed.",
        resolution="Provided renewal instructions. Account unlocked within 24h of resubmission.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.99,
        time_to_resolve_hours=0.5,
    ),
    dict(
        issue_type="KYC_EXPIRED",
        issue_description="RRSP and TFSA both frozen, customer panicking about retirement funds.",
        root_cause="KYC expired. Registered accounts require 3-year renewal.",
        resolution="Reassured customer funds are safe. Renewal docs submitted, accounts restored.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.98,
        time_to_resolve_hours=0.7,
    ),
    # ACCOUNT_FROZEN cases
    dict(
        issue_type="ACCOUNT_FROZEN",
        issue_description="Account suddenly restricted, customer cannot make withdrawals.",
        root_cause="AML review triggered by unusual transaction pattern.",
        resolution="AML review cleared in 48h. Restriction lifted automatically.",
        resolution_type="AUTO_RESOLVED",
        confidence_score=0.88,
        time_to_resolve_hours=2.0,
    ),
]


async def seed_cases(conn: asyncpg.Connection) -> None:
    rows = []
    all_cust_ids = list(CUST.values())

    for template in CASE_TEMPLATES:
        # Generate 4-6 variations of each template
        for _ in range(rng.randint(4, 6)):
            created = days_ago(rng.randint(10, 500))
            resolve_hours = template["time_to_resolve_hours"] * rng.uniform(0.7, 1.5)
            rows.append((
                uid(), rng.choice(all_cust_ids),
                template["issue_type"],
                template["issue_description"],
                jd([]),           # investigation_steps (simplified for seed)
                template["root_cause"],
                template["resolution"],
                template["resolution_type"],
                round(template["confidence_score"] * rng.uniform(0.9, 1.05), 3),
                round(resolve_hours, 2),
                created,
                created + timedelta(hours=resolve_hours),
            ))

    await conn.executemany("""
        INSERT INTO cases
            (case_id, customer_id, issue_type, issue_description,
             investigation_steps, root_cause, resolution, resolution_type,
             confidence_score, time_to_resolve_hours, created_at, resolved_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
    """, rows)
    print(f"  ✓ {len(rows)} historical cases")
    return rows  # type: ignore[return-value]


# ── Demo Issues ───────────────────────────────────────────────────────────────

DEMO_ISSUES = [
    dict(
        issue_id=ISSUE["s1"],
        customer_id=CUST["alex"],
        raw_message=(
            "My $15,000 wire transfer from TD Bank hasn't shown up in 4 business days "
            "and my account seems partially restricted. I need this money urgently to "
            "close on a property purchase."
        ),
        channel="chat", urgency="high",
    ),
    dict(
        issue_id=ISSUE["s2"],
        customer_id=CUST["sarah"],
        raw_message=(
            "I just transferred $20,000 into my RRSP but I received a warning email "
            "from Wealthsimple. Am I going to be penalized by CRA? I'm worried about "
            "the 1% monthly penalty."
        ),
        channel="email", urgency="medium",
    ),
    dict(
        issue_id=ISSUE["s3"],
        customer_id=CUST["james"],
        raw_message=(
            "I just checked my account and there's a sell order on my Apple shares "
            "for $8,400 that I never placed. I did not make this trade. Someone may "
            "have gotten into my account."
        ),
        channel="chat", urgency="critical",
    ),
    dict(
        issue_id=ISSUE["s4"],
        customer_id=CUST["maria"],
        raw_message=(
            "My T5 slip from Wealthsimple shows $1,200 in dividend income, but when "
            "I add up all the dividend payments I received in my account I only get $890. "
            "My accountant says I need to report the T5 amount but I don't understand "
            "the discrepancy. My taxes are due soon."
        ),
        channel="email", urgency="medium",
    ),
    dict(
        issue_id=ISSUE["s5"],
        customer_id=CUST["david"],
        raw_message=(
            "I tried to send $500 to my friend twice because the first one said it "
            "failed. Now both transactions show as failed but only one refund came "
            "back to my account. I'm missing $500."
        ),
        channel="chat", urgency="medium",
    ),
    dict(
        issue_id=ISSUE["s6"],
        customer_id=CUST["emma"],
        raw_message=(
            "My Wealthsimple account is completely locked. I can't log in or access "
            "any of my money. I've had the account for 3 years and nothing like this "
            "has ever happened before. What is going on?"
        ),
        channel="chat", urgency="high",
    ),
]


async def seed_issues(conn: asyncpg.Connection) -> None:
    rows = [
        (i["issue_id"], i["customer_id"], i["raw_message"],
         i["channel"], i["urgency"], "open", now())
        for i in DEMO_ISSUES
    ]
    await conn.executemany("""
        INSERT INTO issues (issue_id, customer_id, raw_message, channel, urgency, status, created_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
    """, rows)
    print(f"  ✓ {len(rows)} demo issues")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n── Seeding PostgreSQL ────────────────────────────────────────────")
    conn = await connect()
    try:
        await truncate(conn)
        await seed_customers(conn)

        # Collect background customer IDs for FK references
        bg_custs = await conn.fetch(
            "SELECT customer_id FROM customers WHERE customer_id NOT LIKE 'cust-%'"
        )
        bg_cust_ids = [r["customer_id"] for r in bg_custs]

        await seed_accounts(conn, bg_cust_ids)

        # Collect background account IDs
        bg_accs = await conn.fetch(
            "SELECT account_id FROM accounts WHERE account_id NOT LIKE 'acc-%'"
        )
        bg_acc_ids = [r["account_id"] for r in bg_accs]

        await seed_transactions(conn, bg_acc_ids)
        await seed_login_events(conn)
        await seed_communications(conn)
        await seed_cases(conn)
        await seed_issues(conn)

        print("── Done ──────────────────────────────────────────────────────────\n")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
