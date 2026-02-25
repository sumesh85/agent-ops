# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this project is

A **Financial Issue Investigation Agent** built for the Wealthsimple AI Builders program. The agent autonomously investigates customer financial issues (wire delays, RRSP over-contributions, unauthorized trades, T5 discrepancies, failed e-transfers, KYC freezes) using Claude + MCP tools over a synthetic PostgreSQL + ChromaDB dataset.

---

## Common commands

All day-to-day operations go through `make`. Everything runs inside Docker.

```bash
make setup          # first-time: copy .env.example → .env, build all images
make up             # start all services in background
make seed           # populate PostgreSQL + ChromaDB with synthetic demo data (idempotent)
make dev            # make up + make seed (full fresh start)
make reset          # make clean + make dev (full wipe and reseed)
make down           # stop all services
make ps             # show service health

# Logs
make logs           # backend
make logs-agent     # agent (Claude tool calls, turn-by-turn)
make logs-mcp       # mcp-server (tool dispatch, cache hits)
make logs-all       # everything

# Shells
make shell          # bash in backend container
make agent-shell    # bash in agent container
make mcp-shell      # bash in mcp-server container
make db-shell       # psql
make redis-shell    # redis-cli

# Quality (runs inside containers)
make lint           # ruff check across backend + agent + mcp-server
make fmt            # ruff format
make typecheck      # mypy on backend
```

Before running: set `ANTHROPIC_API_KEY` in `.env` (copy from `.env.example`).

---

## Service architecture

Three Python services + one Next.js frontend, all orchestrated via Docker Compose:

```
frontend (Next.js 15, :3000)
    └─► backend (FastAPI, :8000)      ← control plane: loads issues, persists run_traces
            └─► agent (FastAPI, :8010) ← investigation loop: Claude + MCP client
                    └─► mcp-server (FastMCP SSE, :8002) ← 8 investigation tools
                                └─► PostgreSQL (:5432)
                                └─► Redis (:6379)       ← tool result cache
                                └─► ChromaDB (:8001)    ← policy docs + case embeddings
```

**Data flow for a single investigation:**
1. Frontend POSTs to `backend /api/v1/investigate/{issue_id}`
2. Backend loads issue from PostgreSQL, POSTs issue context to `agent /run`
3. Agent opens an SSE connection to `mcp-server`, calls `session.list_tools()` to get 8 MCP tools
4. Agent appends `submit_resolution` (defined locally — never in MCP) to the tool list
5. Agent runs Claude `claude-sonnet-4-6` in a tool-use loop (max 15 turns)
6. Each tool call goes via `session.call_tool()` → MCP server → PostgreSQL/Redis/ChromaDB
7. Agent intercepts `submit_resolution` call to capture structured output, exits loop
8. Agent returns `RunResult` dict to backend; backend writes `run_traces` row to PostgreSQL

---

## Service responsibilities (strict boundaries)

| Service | Owns | Does NOT own |
|---|---|---|
| `mcp-server` | Tool implementations, Redis caching, DB reads, ChromaDB queries | Claude, DB writes |
| `agent` | Claude loop, MCP client session, `submit_resolution` schema | DB reads/writes directly |
| `backend` | `run_traces` persistence, issues API, proxying to agent | Tool implementations |
| `frontend` | UI only | Any backend logic |

---

## Key files to know

| File | Purpose |
|---|---|
| `agent/src/runner.py` | Core investigation loop — Claude + MCP client, `submit_resolution` interception, `MAX_TURNS=15` |
| `agent/src/prompts.py` | System prompt — hard escalation rules table, confidence calibration guide |
| `mcp-server/src/server.py` | Entrypoint — imports tool modules (triggers `@mcp.tool()` registration), runs SSE server |
| `mcp-server/src/app.py` | Singleton `FastMCP` instance — imported by all tool modules |
| `mcp-server/src/tools/` | 3 files: `accounts.py` (4 tools), `transactions.py` (2 tools), `knowledge.py` (2 tools) |
| `backend/src/main.py` | FastAPI endpoints: `POST /investigate/{id}`, `GET /issues`, `GET /runs/{trace_id}` |
| `backend/src/db/migrations/001_init.sql` | Full PostgreSQL schema — applied automatically on first container start |
| `backend/scripts/seed_db.py` | Synthetic data generator — creates all 6 demo scenario entities with fixed IDs |
| `backend/scripts/seed_vector.py` | Chunks 8 policy markdown files → ChromaDB; embeds 80 historical cases |
| `docs/policies/` | 8 markdown files ingested into ChromaDB `policies` collection |
| `docs/demo_scenarios.md` | Full investigation paths, expected tool sequences, and structured outputs for all 6 scenarios |

---

## MCP tool registration pattern

Tool modules import the singleton `mcp` and use `@mcp.tool()` decorators:

```python
# In any mcp-server/src/tools/*.py file:
from src.app import mcp

@mcp.tool()
async def my_tool(param: str) -> str:
    """Docstring becomes Claude's tool description."""
    ...
```

`server.py` imports each tool module as a side effect to trigger registration, then calls `mcp.run(transport="sse")`. Adding a new tool means: create the function in a tool file, ensure `server.py` imports it.

---

## `submit_resolution` is special

This terminal tool is **defined only in `agent/src/runner.py`** and never exposed via MCP. When Claude calls it, the agent intercepts it before dispatching to MCP, captures `block.input` as `structured_output`, and exits the loop. Do not add it to the MCP server.

---

## Database schema summary

8 PostgreSQL tables: `customers`, `accounts`, `transactions`, `login_events`, `communications`, `cases`, `issues`, `run_traces`.

- `transactions.status`: `completed | pending | processing | failed | reversed | pending_reversal`
- `transactions.transaction_type`: `deposit | withdrawal | wire_in | wire_out | transfer_in | transfer_out | trade_buy | trade_sell | dividend | drip | etransfer`
- `transactions.metadata` (JSONB): `{device_id, ip_country, instrument, quantity, unit_price, login_session_id}`
- `run_traces.tool_calls` (JSONB): `[{tool, args_digest, latency_ms, cache_hit, result_summary}]`

Schema is in `backend/src/db/migrations/001_init.sql`, applied automatically by PostgreSQL on first container start via `docker-entrypoint-initdb.d`.

---

## Demo scenario fixed IDs

Seed scripts create these exact IDs every run:

| ID | Scenario | Resolution |
|---|---|---|
| `issue-wire-aml-0001` | Wire Transfer + AML Hold | AUTO_RESOLVED |
| `issue-rrsp-over-0002` | RRSP Over-contribution Risk | ESCALATED |
| `issue-unauth-trade-0003` | Unauthorized Trade | ESCALATED (CRITICAL) |
| `issue-t5-mismatch-0004` | T5 Dividend Discrepancy | AUTO_RESOLVED |
| `issue-etransfer-fail-0005` | Failed E-Transfer Refund | AUTO_RESOLVED |
| `issue-kyc-frozen-0006` | KYC Expired — Account Frozen | AUTO_RESOLVED |

---

## Redis caching (in mcp-server)

All tool functions check Redis before hitting PostgreSQL or ChromaDB:

- Tool call results: 60s TTL (`REDIS_TTL_TOOL_CALL`)
- Policy search: 300s TTL (`REDIS_TTL_POLICY`)
- Case similarity: 120s TTL (`REDIS_TTL_CASES`)

Cache key format: `tool:{tool_name}:{sha256_of_kwargs[:16]}`. The agent uses latency < 5ms as a proxy for cache hit since MCP doesn't surface this information.

---

## Frontend routes

| Route | Page |
|---|---|
| `/` | Redirects to `/overview` |
| `/overview` | Stability Overview — confidence bars, demo script, avg confidence ring |
| `/issues` | Issues Dashboard — trigger investigations, see post-run confidence |
| `/runs/[traceId]` | Run Detail — tool trace timeline, policy flags, reasoning accordion, evidence details |

The `StructuredOutput` type has `[key: string]: unknown` to allow scenario-specific extra fields (`evidence_summary`, `security_signals`, `breakdown`, `transaction_summary`) to render automatically in the "Evidence Details" section.

---

## ChromaDB collections

| Collection | Content | Embedding source |
|---|---|---|
| `policies` | 8 policy docs chunked by `##` section | `all-MiniLM-L6-v2` (local, no API) |
| `case_embeddings` | 80 historical resolved cases | same |

ChromaDB runs at `chroma:8000` internally, exposed at `localhost:8001`. The `policy_search` tool accepts an optional `category` filter: `WIRE | TAX | SECURITY | PAYMENT | COMPLIANCE | TRADING`.
