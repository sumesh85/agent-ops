#!/usr/bin/env python3
"""
seed_vector.py — Ingest policy documents and historical cases into ChromaDB.

Collections created:
  - policies       : chunked markdown policy docs (semantic search)
  - case_embeddings: historical resolved case summaries (similarity search)

Run via:  python scripts/seed_vector.py
       or make seed (via seed_all.py)
"""

import asyncio
import os
import re
from pathlib import Path

import asyncpg
import chromadb
from chromadb.config import Settings as ChromaSettings

POLICIES_DIR = Path(os.getenv("POLICIES_DIR", "/app/policies"))
CHROMA_HOST  = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT  = int(os.getenv("CHROMA_PORT", "8001"))


# ── ChromaDB client ───────────────────────────────────────────────────────────

def get_chroma() -> chromadb.HttpClient:  # type: ignore[type-arg]
    return chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


# ── Policy document chunking ──────────────────────────────────────────────────

def chunk_markdown(content: str, source_file: str, category: str) -> list[dict]:  # type: ignore[type-arg]
    """
    Split markdown by ## sections. Each section becomes one chunk.
    Chunks smaller than 80 chars are merged with the previous chunk.
    """
    sections = re.split(r"\n(?=## )", content)
    chunks = []
    buffer = ""

    for section in sections:
        if len(section.strip()) < 80:
            buffer += "\n" + section
            continue
        if buffer:
            section = buffer + "\n" + section
            buffer = ""
        heading_match = re.match(r"## (.+)", section)
        heading = heading_match.group(1).strip() if heading_match else "General"
        chunks.append({
            "content": section.strip(),
            "source_file": source_file,
            "category": category,
            "section": heading,
        })

    if buffer:
        if chunks:
            chunks[-1]["content"] += "\n" + buffer
        else:
            chunks.append({
                "content": buffer.strip(),
                "source_file": source_file,
                "category": category,
                "section": "General",
            })
    return chunks


POLICY_FILES = [
    ("wire_transfers.md",  "WIRE"),
    ("rrsp_rules.md",      "TAX"),
    ("tfsa_rules.md",      "TAX"),
    ("account_security.md","SECURITY"),
    ("etransfer_policy.md","PAYMENT"),
    ("tax_slips.md",       "TAX"),
    ("kyc_compliance.md",  "COMPLIANCE"),
    ("trading_policies.md","TRADING"),
]


def seed_policies(client: chromadb.HttpClient) -> None:  # type: ignore[type-arg]
    col = client.get_or_create_collection(
        name="policies",
        metadata={"hnsw:space": "cosine"},
    )

    # Clear existing docs
    existing = col.get()
    if existing["ids"]:
        col.delete(ids=existing["ids"])
        print(f"  ✓ cleared {len(existing['ids'])} existing policy chunks")

    all_chunks: list[dict] = []  # type: ignore[type-arg]
    for filename, category in POLICY_FILES:
        filepath = POLICIES_DIR / filename
        if not filepath.exists():
            print(f"  ⚠ missing policy file: {filepath}")
            continue
        content = filepath.read_text()
        chunks = chunk_markdown(content, filename, category)
        all_chunks.extend(chunks)
        print(f"  → {filename}: {len(chunks)} chunks")

    if not all_chunks:
        print("  ✗ No policy chunks to ingest!")
        return

    col.add(
        ids=[f"pol-{i:04d}" for i in range(len(all_chunks))],
        documents=[c["content"] for c in all_chunks],
        metadatas=[{
            "source_file": c["source_file"],
            "category":    c["category"],
            "section":     c["section"],
        } for c in all_chunks],
    )
    print(f"  ✓ {len(all_chunks)} policy chunks ingested into ChromaDB")


# ── Case embeddings ───────────────────────────────────────────────────────────

async def fetch_cases() -> list[dict]:  # type: ignore[type-arg]
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "agentops"),
        user=os.getenv("POSTGRES_USER", "agentops"),
        password=os.getenv("POSTGRES_PASSWORD", "agentops_dev_secret"),
    )
    try:
        rows = await conn.fetch("""
            SELECT case_id, issue_type, issue_description,
                   root_cause, resolution, resolution_type, confidence_score
            FROM cases
        """)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


def seed_case_embeddings(client: chromadb.HttpClient, cases: list[dict]) -> None:  # type: ignore[type-arg]
    col = client.get_or_create_collection(
        name="case_embeddings",
        metadata={"hnsw:space": "cosine"},
    )

    existing = col.get()
    if existing["ids"]:
        col.delete(ids=existing["ids"])

    # Format each case as a rich text blob for semantic embedding
    documents = []
    metadatas = []
    ids = []

    for case in cases:
        text = (
            f"Issue type: {case['issue_type']}\n"
            f"Issue: {case['issue_description']}\n"
            f"Root cause: {case['root_cause']}\n"
            f"Resolution: {case['resolution']}\n"
            f"Outcome: {case['resolution_type']}"
        )
        documents.append(text)
        metadatas.append({
            "issue_type":      case["issue_type"],
            "resolution_type": case["resolution_type"],
            "confidence_score": str(case["confidence_score"]),
        })
        ids.append(case["case_id"])

    col.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"  ✓ {len(cases)} case embeddings ingested into ChromaDB")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n── Seeding ChromaDB ──────────────────────────────────────────────")
    client = get_chroma()

    print("  Ingesting policy documents...")
    seed_policies(client)

    print("  Fetching historical cases from PostgreSQL...")
    cases = await fetch_cases()
    print(f"  Embedding {len(cases)} cases...")
    seed_case_embeddings(client, cases)

    print("── Done ──────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    asyncio.run(main())
