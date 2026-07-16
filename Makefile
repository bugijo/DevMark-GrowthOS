SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

COMPOSE := docker compose
VENV := .venv/bin

.PHONY: help setup install up down reset logs status migrate seed \
	test test-backend test-worker test-frontend lint lint-backend lint-worker lint-frontend \
	e2e validate

help: ## Lista os comandos disponíveis
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Prepara o ambiente e sobe a stack Docker com dados demo
	./scripts/setup.sh

install: ## Instala dependências Python e Node para desenvolvimento
	./scripts/dev-install.sh

up: ## Sobe todos os serviços locais
	$(COMPOSE) up --build -d

down: ## Encerra a stack preservando volumes
	$(COMPOSE) down

reset: ## Remove stack e volumes locais deliberadamente
	$(COMPOSE) down -v --remove-orphans

logs: ## Acompanha logs dos processos da aplicação
	$(COMPOSE) logs -f backend worker frontend

status: ## Exibe estado e healthchecks
	$(COMPOSE) ps

migrate: ## Aplica migrations do backend
	$(COMPOSE) exec backend alembic upgrade head

seed: ## Reaplica o seed fictício e idempotente
	$(COMPOSE) exec backend python -m growthos.seed

test: test-backend test-worker test-frontend ## Executa testes unitários e de integração locais

test-backend: ## Executa testes do backend
	$(VENV)/pytest backend/tests

test-worker: ## Executa testes do worker
	$(VENV)/pytest worker/tests

test-frontend: ## Executa testes do frontend
	npm --prefix frontend test

lint: lint-backend lint-worker lint-frontend ## Executa lint e checagem de tipos

lint-backend: ## Valida backend com Ruff e mypy
	$(VENV)/ruff check backend
	$(VENV)/ruff format --check backend
	$(VENV)/mypy --config-file backend/pyproject.toml backend/growthos

lint-worker: ## Valida worker com Ruff e mypy
	$(VENV)/ruff check worker
	$(VENV)/ruff format --check worker
	$(VENV)/mypy --config-file worker/pyproject.toml worker/src/growthos_worker

lint-frontend: ## Valida frontend com ESLint, TypeScript e build
	npm --prefix frontend run lint
	npm --prefix frontend run typecheck
	npm --prefix frontend run build

e2e: ## Executa o fluxo vertical com Playwright no profile test
	./scripts/run-e2e.sh

validate: ## Valida Compose, scripts, JSON, Python e whitespace
	./scripts/validate.sh
