BACKEND := backend
VENV := $(BACKEND)/.venv
BIN := $(CURDIR)/$(VENV)/bin
MARKER := $(VENV)/.installed

.PHONY: install lint format typecheck test run up down migrate migrate-down venv reinstall pre-commit-install pre-commit

REV ?= -1

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
	cd $(BACKEND) && $(BIN)/pytest

pre-commit-install: $(MARKER)
	$(BIN)/pre-commit install

pre-commit: $(MARKER)
	$(BIN)/pre-commit run --all-files

run: $(MARKER)
	cd $(BACKEND) && $(BIN)/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker compose up --build

down:
	docker compose down

migrate: $(MARKER)
	cd $(BACKEND) && $(BIN)/alembic upgrade head

migrate-down: $(MARKER)
	cd $(BACKEND) && $(BIN)/alembic downgrade $(REV)

venv: $(VENV)/bin/python
