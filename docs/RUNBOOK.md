# Casepilot — Runbook

Step-by-step instructions to start, seed, and test the full stack locally.

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Docker Desktop | 24+ | `docker --version` |
| Docker Compose | v2 (bundled) | `docker compose version` |
| Anthropic API key | — | [console.anthropic.com](https://console.anthropic.com) |

---

## Step 1 — Clone and configure

```bash
# 1a. Enter the project directory
cd /path/to/agent-ops

# 1b. Copy the environment template
cp .env.example .env
```

Open `.env` and set your API key:

```env
ANTHROPIC_API_KEY=sk-ant-...your-key-here...
```

Everything else in `.env` can stay as-is for local development.

---

## Step 2 — Build all images

```bash
make setup
```

This runs `docker compose build --parallel` across all 5 services:
- `db` — PostgreSQL 16
- `redis` — Redis 7
- `chroma` — ChromaDB 0.6.3
- `mcp-server` — MCP tool server (port 8002)
- `agent` — Claude investigation runner (port 8010)
- `backend` — FastAPI control plane (port 8000)
- `frontend` — Next.js 15 UI (port 3000)

Expected output: `✓ Setup complete. Run 'make dev' to start.`

---

## Step 3 — Start the stack

```bash
make up
```

Services start in dependency order:
1. `db`, `redis`, `chroma` (infrastructure)
2. `mcp-server` (waits for db + redis + chroma healthy)
3. `agent` (waits for mcp-server healthy)
4. `backend` (waits for db + redis + agent healthy)
5. `frontend` (waits for backend healthy)

Check all services are running:

```bash
make ps
```

All services should show `healthy` within ~60 seconds.

---

## Step 4 — Seed the database

```bash
make seed
```

This runs a one-shot container that executes `scripts/seed_all.py`, which:

1. **`seed_db.py`** — truncates all tables, then inserts:
   - 10 customers (6 scenario-specific + 4 background)
   - 18 accounts (TFSA, RRSP, Cash, Crypto across all customers)
   - ~800 transactions (scenario-specific states + background noise)
   - ~200 login events (including Romanian login for Scenario 3)
   - 60 communications (KYC reminder emails for Scenario 6)
   - 80 historical resolved cases
   - **6 demo issues** (one per scenario, with fixed IDs)

2. **`seed_vector.py`** — chunks 8 policy markdown files and ingests them into ChromaDB, then embeds the 80 historical cases into the `case_embeddings` collection.

Expected output:
```
✓ seed_db complete  (tables truncated + repopulated)
✓ seed_vector complete  (policies + cases embedded)

Demo Issue IDs:
  issue-wire-aml-0001     Wire Transfer + AML Hold
  issue-rrsp-over-0002    RRSP Over-contribution Risk
  issue-unauth-trade-0003 Unauthorized Trade
  issue-t5-mismatch-0004  T5 Dividend Discrepancy
  issue-etransfer-fail-0005 Failed E-Transfer Refund
  issue-kyc-frozen-0006   KYC Expired — Account Frozen
```

> **Seed is idempotent.** Run `make seed` again at any time to reset to a clean state.

---

## Step 5 — Verify services are up

```bash
# Backend health
curl http://localhost:8000/health
# → {"status": "ok", "env": "development"}

# Agent health
curl http://localhost:8010/health
# → {"status": "ok", "model": "claude-sonnet-4-6"}

# MCP server SSE endpoint
curl -N http://localhost:8002/sse
# → event: ... (streaming SSE — Ctrl+C to exit)
```

---

## Step 6 — Open the UI

Navigate to **http://localhost:3000**

This redirects to the **Stability Overview** page (`/overview`), which shows:
- 6 scenario cards with confidence bars (empty until investigated)
- Demo script timeline
- Avg confidence ring (populates after investigations run)

---

## Step 7 — Run an investigation

### Option A — Via the UI

1. Click **Issues** in the left sidebar
2. Click **Investigate** on any scenario card
3. Wait 15–45 seconds (Claude + MCP tool calls)
4. Click **View Run Detail** to see the full trace

### Option B — Via curl

```bash
# Trigger Scenario 1: Wire Transfer + AML Hold
curl -X POST http://localhost:8000/api/v1/investigate/issue-wire-aml-0001

# Trigger Scenario 3: Unauthorized Trade (critical escalation)
curl -X POST http://localhost:8000/api/v1/investigate/issue-unauth-trade-0003

# Trigger Scenario 4: T5 Dividends (auto-resolved, fast)
curl -X POST http://localhost:8000/api/v1/investigate/issue-t5-mismatch-0004
```

The response is the full RunResult JSON including `tool_calls`, `structured_output`, `confidence_score`, and `policy_flags`.

### Option C — Trigger all 6 at once

```bash
for id in \
  issue-wire-aml-0001 \
  issue-rrsp-over-0002 \
  issue-unauth-trade-0003 \
  issue-t5-mismatch-0004 \
  issue-etransfer-fail-0005 \
  issue-kyc-frozen-0006; do
  echo "→ Investigating $id..."
  curl -s -X POST http://localhost:8000/api/v1/investigate/$id \
    | python3 -c "import sys,json; r=json.load(sys.stdin); print(f'  {r[\"status\"]} | confidence={r[\"confidence_score\"]} | flags={r[\"policy_flags\"]}')"
done
```

---

## Step 8 — Verify results

### List all issues with run status

```bash
curl -s http://localhost:8000/api/v1/issues | python3 -m json.tool | head -60
```

### Retrieve a specific run trace

```bash
# Get the trace_id from the investigate response, then:
curl -s http://localhost:8000/api/v1/runs/<trace_id> | python3 -m json.tool
```

### Check ChromaDB collections

```bash
curl http://localhost:8001/api/v1/collections
# Should show: policies (8 docs), case_embeddings (80 docs)
```

### Check Redis cache

```bash
make redis-shell
# Inside redis-cli:
KEYS tool:*        # lists all cached tool calls
TTL tool:policy*   # check TTL on a policy cache entry
```

---

## Expected investigation outcomes

| Scenario | Expected outcome | Confidence | Flags |
|---|---|---|---|
| Wire + AML Hold | AUTO_RESOLVED | ~0.85–0.92 | `AML_REVIEW_TRIGGERED` |
| RRSP Over-contribution | ESCALATED | ~0.50–0.60 | `TAX_ADVICE_REQUIRED`, `CRA_PENALTY_RISK` |
| Unauthorized Trade | ESCALATED (CRITICAL) | ~0.90–0.96 | `FRAUD_SUSPECTED`, `MANDATORY_ESCALATION` |
| T5 Dividends | AUTO_RESOLVED | ~0.95–0.99 | `TAX_RELATED` |
| Failed E-Transfer | AUTO_RESOLVED | ~0.88–0.94 | none |
| KYC Frozen | AUTO_RESOLVED | ~0.96–0.99 | `KYC_COMPLIANCE` |

---

## Logs and debugging

```bash
# All service logs live
make logs-all

# Agent logs (Claude tool calls, turn-by-turn)
make logs-agent

# MCP server logs (tool dispatch, cache hits)
make logs-mcp

# Backend logs (HTTP requests, trace persistence)
make logs

# Open a shell in any container
make shell          # backend
make agent-shell    # agent
make mcp-shell      # mcp-server
make db-shell       # psql
make redis-shell    # redis-cli
```

---

## API reference (quick)

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Backend health check |
| `/api/v1/issues` | GET | List all issues with run status |
| `/api/v1/investigate/{issue_id}` | POST | Trigger investigation (sync, ~15–45s) |
| `/api/v1/runs/{trace_id}` | GET | Retrieve full run trace |
| `http://localhost:8010/health` | GET | Agent health check |
| `http://localhost:8010/docs` | GET | Agent OpenAPI docs |
| `http://localhost:8002/sse` | GET | MCP server SSE stream |
| `http://localhost:8001/api/v1/collections` | GET | ChromaDB collections |

---

## Full reset

To wipe all data and start fresh:

```bash
make reset
```

This runs `make clean` (removes all containers + volumes) followed by `make dev` (rebuild + reseed).

---

## Troubleshooting

**`make seed` fails with connection error**
→ Run `make ps` — ensure `db` and `chroma` are `healthy` before seeding.
→ Wait 30s after `make up` for health checks to pass, then retry.

**Agent returns 503 "Agent service unreachable"**
→ Check `make logs-agent`. The agent waits for `mcp-server` to be healthy.
→ MCP server SSE health check can take ~15s on first start (ChromaDB embedding model loads).

**Investigation times out or returns 500**
→ Verify `ANTHROPIC_API_KEY` is set correctly in `.env`.
→ Check `make logs-agent` for the Claude API error.

**ChromaDB collections are empty after seed**
→ Seed runs against the `chroma` container via HTTP. Confirm `chroma` is healthy: `curl http://localhost:8001/api/v1/heartbeat`
→ Run `make seed` again — it is safe to re-run.

**Policy search returns 0 results**
→ Check if the `policies` collection has documents: `curl http://localhost:8001/api/v1/collections/policies/count`
→ If count is 0, run `make seed` again.
