BACKEND := backend
VENV := $(BACKEND)/.venv
BIN := $(CURDIR)/$(VENV)/bin
MARKER := $(VENV)/.installed

-include .env
APP_PORT ?= 8000

.PHONY: install lint format typecheck test run up down up-prod down-prod migrate migrate-test migrate-create migrate-down venv reinstall pre-commit-install pre-commit frontend-install frontend-dev frontend-build seed seed-marketplace seed-achievements reindex-embeddings wallet staff preset-export preset-import telegram-up telegram-down

FRONTEND := frontend

REV ?= -1
POSTGRES_PORT ?= 5432
TEST_DATABASE_URL ?= postgresql+psycopg://mood:mood@localhost:$(POSTGRES_PORT)/mood_tracker_test

$(VENV)/bin/python:
	python3 -m venv $(VENV)

$(MARKER): $(BACKEND)/pyproject.toml $(VENV)/bin/python
	$(BIN)/pip install -e "$(CURDIR)/$(BACKEND)[dev]"
	@touch $(MARKER)

install: $(MARKER)
	@echo "Ready: dependencies installed in $(VENV)"

reinstall:
	rm -rf $(VENV)
	@$(MAKE) install

lint: $(MARKER)
	cd $(BACKEND) && $(BIN)/ruff check app tests
	cd $(BACKEND) && $(BIN)/ruff format --check app tests

format: $(MARKER)
	cd $(BACKEND) && $(BIN)/ruff format app tests
	cd $(BACKEND) && $(BIN)/ruff check --fix app tests

typecheck: $(MARKER)
	cd $(BACKEND) && $(BIN)/mypy app

test: $(MARKER)
	cd $(BACKEND) && TEST_DATABASE_URL='$(TEST_DATABASE_URL)' $(BIN)/pytest

migrate-test: $(MARKER)
	cd $(BACKEND) && DATABASE_URL='$(TEST_DATABASE_URL)' $(BIN)/alembic upgrade head

pre-commit-install: $(MARKER)
	$(BIN)/pre-commit install

pre-commit: $(MARKER)
	$(BIN)/pre-commit run --all-files

run: $(MARKER)
	cd $(BACKEND) && $(BIN)/uvicorn app.main:app --reload --host 0.0.0.0 --port $(APP_PORT)

up:
	docker compose build && docker compose up

up-no-cache:
	docker compose build --no-cache && docker compose up

down:
	docker compose down

# ngrok webhook + Cloudflare Mini App. Vite must already be running.
telegram-up:
	./scripts/dev-telegram-up.sh

telegram-down:
	./scripts/dev-telegram-up.sh --stop

# Prod-shaped stack (nginx UI + API, no Vite / --reload). Uses .env.prod.
# `--profile mail` starts MailHog for local email smoke; omit on a real VPS.
up-prod:
	@test -f .env.prod || cp .env.prod.example .env.prod
	docker compose -f docker-compose.prod.yml --env-file .env.prod --profile mail up --build

down-prod:
	docker compose -f docker-compose.prod.yml --env-file .env.prod --profile mail down

migrate: $(MARKER)
	cd $(BACKEND) && $(BIN)/alembic upgrade head

migrate-create: $(MARKER)
	cd $(BACKEND) && $(BIN)/alembic revision --autogenerate -m "$(MSG)"

migrate-down: $(MARKER)
	cd $(BACKEND) && $(BIN)/alembic downgrade $(REV)

frontend-install:
	cd $(FRONTEND) && npm install

frontend-dev:
	cd $(FRONTEND) && npm run dev

frontend-build:
	cd $(FRONTEND) && npm run build

# Local-only mock data (see backend/dev_seed/). Pass args via SEED_ARGS, e.g.:
#   make seed SEED_ARGS='--seed 7 --users 3 --days 14'
# Overrides MinIO host for host-side runs (Compose publishes MINIO_API_PORT).
SEED_ARGS ?=
MINIO_API_PORT ?= 9000
seed: $(MARKER)
	cd $(BACKEND) && MINIO_ENDPOINT=localhost:$(MINIO_API_PORT) $(BIN)/python -m dev_seed $(SEED_ARGS)

# Official catalog packs from backend/app/data/marketplace/<pack>/.
# Requires a running app container (`make up`).
seed-marketplace:
	docker compose exec -T app python -m app.services.marketplace_seed

# Achievement catalog from backend/app/data/achievements/catalog.json.
# Run after seed-marketplace when rewards reference packs/icons.
seed-achievements:
	docker compose exec -T app python -m app.services.achievements.seed

# Ledger-backed wallet ops. Do not UPDATE user_wallets by hand.
#   make wallet WALLET_ARGS='grant --user you@example.com --amount 500 --note beta'
#   make wallet WALLET_ARGS='reconcile --user you@example.com --note "manual DB +500"'
#   make wallet WALLET_ARGS='revoke --user you@example.com --pack random-pics --note qa'
WALLET_ARGS ?= --help
wallet: $(MARKER)
	cd $(BACKEND) && $(BIN)/python -m app.cli.wallet $(WALLET_ARGS)

# Staff role (token grants, official packs, presets in the /staff console).
#   make staff STAFF_ARGS='grant --user you@example.com'
STAFF_ARGS ?= list
staff: $(MARKER)
	cd $(BACKEND) && $(BIN)/python -m app.cli.staff $(STAFF_ARGS)

# Catalog presets (packs + achievements) for bootstrapping another instance.
#   make preset-export PRESET=../preset.zip PRESET_ARGS='--pack foxes --no-achievements'
#   make preset-import PRESET=../preset.zip
# PRESET is relative to backend/. Host-side run, so MinIO goes through MINIO_API_PORT.
PRESET ?= ../preset.zip
PRESET_ARGS ?=
preset-export: $(MARKER)
	cd $(BACKEND) && MINIO_ENDPOINT=localhost:$(MINIO_API_PORT) $(BIN)/python -m app.cli.presets export --out $(PRESET) $(PRESET_ARGS)

preset-import: $(MARKER)
	cd $(BACKEND) && MINIO_ENDPOINT=localhost:$(MINIO_API_PORT) $(BIN)/python -m app.cli.presets import $(PRESET)

# Recompute semantic-search embeddings for all mood entries (requires EMBEDDING_ENABLED=true).
reindex-embeddings: $(MARKER)
	cd $(BACKEND) && $(BIN)/python -m app.jobs.reindex_embeddings

venv: $(VENV)/bin/python
