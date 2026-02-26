# Next Steps — AgentOps Roadmap

Current state: **MVP + Human-in-the-Loop Escalation + Business Metrics Dashboard** ✅

---

## 2. Auto-Trigger on New Issues *(closes the loop)*

**Business value:** Makes this a real operational tool, not a demo button.

**What to build:**
- Background worker in backend that polls `issues WHERE status = 'open'` every 30s
- Optionally: webhook `POST /api/v1/issues/ingest` to receive new issues from Salesforce/Zendesk/Intercom
- Auto-dispatch to agent; mark issue `status = 'investigating'` before dispatch to prevent double-runs
- On result: mark `status = 'resolved'` or `status = 'escalated'`

**Files to touch:**
- `backend/src/main.py` — add `POST /api/v1/issues/ingest` (create issue + auto-trigger)
- `backend/src/worker.py` (new) — async polling loop with `asyncio.create_task`
- `backend/src/db/migrations/` — no schema changes needed

---

## 3. Business Metrics Dashboard *(sells the value)*

**Business value:** Answers "what's the ROI?" for any stakeholder.

**What to build:**
- `/analytics` page with charts:
  - Resolution rate over time (auto-resolved vs escalated)
  - Average confidence score (rolling 7/30 days)
  - Escalation rate by urgency tier
  - Time-to-resolve (p50/p95) by issue type
  - Token cost per resolution (token_count × model price)
- Aggregation queries against `run_traces` + `issues`

**Files to touch:**
- `backend/src/main.py` — add `GET /api/v1/analytics/summary`
- `frontend/src/app/analytics/page.tsx` (new)
- `frontend/src/components/SidebarNav.tsx` — enable Analytics link
- Consider: `recharts` or `tremor` for chart components

---

## 4. Replay / Stability Engine *(ops credibility)*

**Business value:** Proves the agent is robust, not brittle. Critical for production sign-off.

**What to build:**
- `POST /api/v1/replay/{trace_id}` — re-run the same issue with N perturbations (paraphrase raw_message slightly)
- Compare outputs: did resolution_type/escalate/confidence_score stay consistent?
- Stability score = % of perturbations that match original resolution
- `/stability` page: per-scenario stability bars, variance heatmap

**Files to touch:**
- `backend/src/main.py` — add replay endpoint
- `agent/src/runner.py` — accept optional `replay_seed` param for determinism
- `frontend/src/app/stability/page.tsx` (new)
- `frontend/src/components/SidebarNav.tsx` — enable Replay + Stability links
- `backend/src/db/migrations/003_replay_runs.sql` (new) — `replay_runs` table

---

## 5. Drift Monitoring + Alerts *(production readiness)*

**Business value:** Catches model degradation before it impacts customers.

**What to build:**
- Scheduled job (every hour) that computes rolling metrics:
  - 7-day avg confidence score vs baseline
  - Escalation rate (%) vs baseline
  - Policy flag frequency by type
- Alert thresholds: if confidence drops >10% or escalation rate spikes >20%, fire alert
- Notification channel: Slack webhook or email (configurable in `.env`)
- Alert log stored in `alerts` table; surfaced on Overview page

**Files to touch:**
- `backend/src/drift.py` (new) — metric computation + threshold checks
- `backend/src/main.py` — register drift check as background task on startup
- `backend/src/db/migrations/004_alerts.sql` (new) — `drift_alerts` table
- `frontend/src/app/overview/page.tsx` — add alert banner when drift detected
- `.env.example` — add `SLACK_WEBHOOK_URL`

---

## Quick wins (can be done anytime)

| Item | Effort | Value |
|---|---|---|
| Paginate `/api/v1/issues` and `/api/v1/escalations` | 1h | Needed once real data grows |
| Add `reviewer` dropdown in escalation form (real agent names) | 30min | Demo polish |
| Export run trace as JSON/PDF | 2h | Audit/compliance requirement |
| Dark/light theme toggle | 1h | Demo preference |
| Add `GET /api/v1/runs?issue_id=X` to fetch run by issue | 30min | Frontend convenience |
