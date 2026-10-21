# Oportuna — comandos habituales
.PHONY: up down logs ps migrate seed ingest test lint fmt dev-api dev-web db-up db-down reset

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=120

ps:
	docker compose ps

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m oportuna.seed

ingest:
	docker compose exec api python -m oportuna.cli ingest

# Local development without Docker for the app processes
db-up:
	docker compose up -d db redis

db-down:
	docker compose stop db redis

dev-api:
	cd apps/api && ../../.venv/bin/uvicorn oportuna.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

test:
	cd apps/api && ../../.venv/bin/python -m pytest -q

lint:
	cd apps/api && ../../.venv/bin/ruff check oportuna tests

fmt:
	cd apps/api && ../../.venv/bin/ruff format oportuna tests

reset:
	docker compose down -v
