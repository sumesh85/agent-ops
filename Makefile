# ── AgentOps Control Plane ─────────────────────────────────────────────────────
# make help   → list all targets
# make dev    → full local stack (build → up → seed)

SHELL        := /bin/bash
COMPOSE      := docker compose
BACKEND_CTR  := agent-ops-backend-1
AGENT_CTR    := agent-ops-agent-1
MCP_CTR      := agent-ops-mcp-server-1

.DEFAULT_GOAL := help

# ── Colours ─────────────────────────────────────────────────────────────────────
CYAN  := \033[0;36m
RESET := \033[0m

# ── Bootstrap ───────────────────────────────────────────────────────────────────
.PHONY: setup
setup: ## Copy .env, build images — run once after clone
	@[ -f .env ] || cp .env.example .env && echo ".env created — add your ANTHROPIC_API_KEY"
	$(COMPOSE) build --parallel
	@echo -e "$(CYAN)✓ Setup complete. Run 'make dev' to start.$(RESET)"

# ── Lifecycle ────────────────────────────────────────────────────────────────────
.PHONY: up down restart
up: ## Start all services in background
	$(COMPOSE) up -d
	@echo -e "$(CYAN)✓ UI         → http://localhost:3000$(RESET)"
	@echo -e "$(CYAN)✓ API        → http://localhost:8000/docs$(RESET)"
	@echo -e "$(CYAN)✓ Agent      → http://localhost:8010/docs$(RESET)"
	@echo -e "$(CYAN)✓ MCP server → http://localhost:8002/sse$(RESET)"

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all app services (backend + agent + mcp-server)
	$(COMPOSE) restart backend agent mcp-server

restart-backend: ## Restart backend only
	$(COMPOSE) restart backend

restart-agent: ## Restart agent only
	$(COMPOSE) restart agent

# ── Data ─────────────────────────────────────────────────────────────────────────
.PHONY: migrate
migrate: ## Apply SQL migrations in order (idempotent — safe to re-run)
	@set -a; . ./.env; set +a; \
	for f in backend/src/db/migrations/*.sql; do \
		echo "Applying $$f..."; \
		$(COMPOSE) exec -T db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB} -f - < $$f; \
	done
	@echo -e "$(CYAN)✓ Migrations applied.$(RESET)"

.PHONY: seed
seed: ## Seed PostgreSQL + ChromaDB with synthetic demo data
	$(COMPOSE) run --rm seed

.PHONY: wait-healthy
wait-healthy: ## Poll backend /health until all services are ready (120s timeout)
	@echo "Waiting for services to be healthy..."
	@for i in $$(seq 1 60); do \
		curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "✓ All services healthy." && exit 0; \
		printf "."; sleep 2; \
	done; \
	echo ""; echo "ERROR: Timed out after 120s waiting for backend health check." ; exit 1

.PHONY: dev
dev: up wait-healthy ## Full dev start: services up + migrate + seed data loaded
	$(MAKE) migrate
	$(MAKE) seed

# ── Logs ─────────────────────────────────────────────────────────────────────────
.PHONY: logs logs-all logs-agent logs-mcp logs-db logs-redis
logs: ## Tail backend logs
	$(COMPOSE) logs -f backend

logs-all: ## Tail all service logs
	$(COMPOSE) logs -f

logs-agent: ## Tail agent logs
	$(COMPOSE) logs -f agent

logs-mcp: ## Tail mcp-server logs
	$(COMPOSE) logs -f mcp-server

logs-db: ## Tail postgres logs
	$(COMPOSE) logs -f db

logs-redis: ## Tail redis logs
	$(COMPOSE) logs -f redis

# ── Shells ───────────────────────────────────────────────────────────────────────
.PHONY: shell agent-shell mcp-shell db-shell redis-shell
shell: ## Open bash in backend container
	$(COMPOSE) exec backend bash

agent-shell: ## Open bash in agent container
	$(COMPOSE) exec agent bash

mcp-shell: ## Open bash in mcp-server container
	$(COMPOSE) exec mcp-server bash

db-shell: ## Open psql shell
	$(COMPOSE) exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

redis-shell: ## Open redis-cli
	$(COMPOSE) exec redis redis-cli

# ── Quality ──────────────────────────────────────────────────────────────────────
.PHONY: lint fmt typecheck test ci
lint: ## Run ruff linter across all services
	$(COMPOSE) exec backend ruff check src/ scripts/
	$(COMPOSE) exec agent ruff check src/
	$(COMPOSE) exec mcp-server ruff check src/

fmt: ## Format code with ruff across all services
	$(COMPOSE) exec backend ruff format src/ scripts/
	$(COMPOSE) exec agent ruff format src/
	$(COMPOSE) exec mcp-server ruff format src/

typecheck: ## Run mypy on backend
	$(COMPOSE) exec backend mypy src/

test: ## Run pytest
	$(COMPOSE) exec backend pytest tests/ -v --tb=short

ci: lint typecheck test ## Run full CI checks locally

# ── Maintenance ──────────────────────────────────────────────────────────────────
.PHONY: clean reset ps
clean: ## Remove containers + all volumes (destructive)
	$(COMPOSE) down -v --remove-orphans
	@echo -e "$(CYAN)✓ All containers and volumes removed.$(RESET)"

reset: clean dev ## Full wipe and restart with fresh seed data

ps: ## Show service status
	$(COMPOSE) ps

# ── Help ─────────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "$(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'
