#!/usr/bin/env python3
"""
seed_all.py — Orchestrates the full seed pipeline.

Order:
  1. seed_db.py    → PostgreSQL (customers, accounts, transactions, cases, issues)
  2. seed_vector.py → ChromaDB  (policy chunks, case embeddings)

Idempotent: safe to run repeatedly.
"""

import asyncio
import sys
import time

# Ensure project root is on path when run directly
sys.path.insert(0, "/app")

from scripts.seed_db import main as seed_db
from scripts.seed_vector import main as seed_vector


async def main() -> None:
    start = time.monotonic()

    await seed_db()
    await seed_vector()

    elapsed = time.monotonic() - start
    print(f"✓ Full seed complete in {elapsed:.1f}s")
    print("  Demo issues ready:")
    print("    S1 — Wire + AML Hold    → issue-wire-aml-0001")
    print("    S2 — RRSP Over-contrib  → issue-rrsp-over-0002")
    print("    S3 — Unauthorized Trade → issue-unauth-trade-0003")
    print("    S4 — T5 Mismatch        → issue-t5-mismatch-0004")
    print("    S5 — Failed E-Transfer  → issue-etransfer-fail-0005")
    print("    S6 — KYC Frozen         → issue-kyc-frozen-0006")
    print()


if __name__ == "__main__":
    asyncio.run(main())
