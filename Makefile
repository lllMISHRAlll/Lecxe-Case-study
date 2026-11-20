# Procurement Assistant: common tasks. Run `make help`.
BACKEND := cd backend &&
PY := $(BACKEND) uv run
GATED := app/rbac/*,app/sql/validator.py,app/guardrails/masker.py,app/po/repository.py,app/po/totals.py,app/normalisation/runner.py

.PHONY: help install testdb up down dev-backend dev-frontend migrate lint test coverage-gates \
        test-frontend test-smoke eval-deepeval test-all normalise-preview normalise-apply \
        normalise-rollback seed-e2e

help:
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ :/'

install: ## Install backend and frontend dependencies
	$(BACKEND) uv sync
	cd frontend && npm ci

testdb: ## Start the local test Postgres
	docker compose up -d --wait testdb

up: ## Run the whole app in Docker (http://localhost:3000)
	docker compose up --build -d --wait backend frontend

down: ## Stop all containers
	docker compose down

dev-backend: ## Backend with reload on http://localhost:8000
	$(PY) uvicorn app.main:create_app --factory --reload --port 8000

dev-frontend: ## Frontend on http://localhost:3000
	cd frontend && BACKEND_URL=http://localhost:8000 npm run dev

migrate: ## Create or upgrade the assistant schema in the company DB
	$(PY) python -m app.db.migrate

lint: ## Lint and type-check both apps
	$(PY) ruff check app tests scripts evals
	cd frontend && npm run lint && npm run typecheck

test: testdb ## Backend tests with coverage gates
	$(PY) pytest --cov=app --cov-branch --cov-report=term-missing:skip-covered --cov-fail-under=90
	$(MAKE) coverage-gates

coverage-gates: ## 100% branch coverage for the security-critical modules
	$(PY) coverage report --include="$(GATED)" --fail-under=100

test-frontend: ## Frontend tests with coverage gates
	cd frontend && npm run test:coverage

test-smoke: ## Read-only checks against the real company DB
	$(PY) pytest -m smoke tests/smoke

eval-deepeval: testdb ## Per-role DeepEval suite (Anthropic judge; needs ANTHROPIC_API_KEY)
	$(PY) python -m evals.deepeval_run

test-all: test test-frontend ## Everything except smoke and evals

seed-e2e: testdb ## Seed the local database used by evals and demos
	$(PY) python -m scripts.seed_e2e

normalise-preview: ## Show what the data-cleaning changes would do (no writes)
	$(PY) python -m scripts.normalise preview

normalise-apply: ## Apply data-cleaning changes to the company DB (logged, with backups)
	$(PY) python -m scripts.normalise apply --yes

normalise-rollback: ## Roll back one change: make normalise-rollback CHANGE=001
	$(PY) python -m scripts.normalise rollback --change $(CHANGE)
