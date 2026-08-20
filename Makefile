.PHONY: dev prod deploy logs backup restore test lint migrate clean build help

# ─────────────────────────────────────────────────────────────────────────────
# Inmobiliaria Platform — Makefile
# ─────────────────────────────────────────────────────────────────────────────

# Detect Compose v2 plugin (`docker compose`) vs standalone binary (`docker-compose`).
COMPOSE ?= $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo docker-compose)

# Default target
help:
	@echo "Inmobiliaria Platform - Makefile Commands"
	@echo "=========================================="
	@echo ""
	@echo "Development:"
	@echo "  make dev          Start development environment (hot reload)"
	@echo "  make seed         Populate database with test data"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linting checks"
	@echo "  make migrate      Run database migrations"
	@echo ""
	@echo "Production:"
	@echo "  make prod         Start production environment (2 API replicas)"
	@echo "  make deploy       Deploy with scaling (3 API replicas)"
	@echo "  make logs         Tail production logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make backup       Create database backup"
	@echo "  make restore      Restore from backup (prompts for file)"
	@echo "  make clean        Remove all containers, volumes, and images"
	@echo ""
	@echo "Build:"
	@echo "  make build        Build Docker images without starting"
	@echo ""

# ── Development ───────────────────────────────────────────────────────────────

dev:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Development environment started. Access:"
	@echo "  API:      http://localhost:8000"
	@echo "  Docs:     http://localhost:8000/docs"
	@echo "  Redis:    localhost:6379"
	@echo "  Postgres: localhost:5432"

# ── Production ───────────────────────────────────────────────────────────────

prod:
	$(COMPOSE) -f docker-compose.prod.yml up -d --build
	@echo "Production environment started."
	@echo "  Run 'make migrate' to apply migrations"
	@echo "  Run 'make logs' to view logs"

deploy:
	$(COMPOSE) -f docker-compose.prod.yml up -d --build --scale api=3
	@echo "Deployed with 3 API replicas."

logs:
	$(COMPOSE) -f docker-compose.prod.yml logs -f --tail=100

logs-api:
	$(COMPOSE) -f docker-compose.prod.yml logs -f api --tail=100

logs-postgres:
	$(COMPOSE) -f docker-compose.prod.yml logs -f postgres --tail=50

logs-redis:
	$(COMPOSE) -f docker-compose.prod.yml logs -f redis --tail=50

logs-celery:
	$(COMPOSE) -f docker-compose.prod.yml logs -f celery-worker celery-beat --tail=100

# ── Maintenance ───────────────────────────────────────────────────────────────

backup:
	$(COMPOSE) -f docker-compose.prod.yml exec -T postgres /backups/backup.sh

restore:
	@echo "Available backups:"
	@$(COMPOSE) -f docker-compose.prod.yml exec -T postgres ls -lh /backups/*.sql.gz 2>/dev/null || echo "No backups found"
	@echo ""
	@read -p "Enter backup filename: " FILE; \
	$(COMPOSE) -f docker-compose.prod.yml exec -T postgres /backups/restore.sh "/backups/$$FILE"

migrate:
	$(COMPOSE) -f docker-compose.prod.yml exec api alembic upgrade head

migrate-create:
	@read -p "Migration name: " NAME; \
	$(COMPOSE) -f docker-compose.prod.yml exec api alembic revision --autogenerate -m "$$NAME"

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	python -m pytest tests/ -v --tb=short

test-unit:
	python -m pytest tests/unit/ -v --tb=short

test-integration:
	python -m pytest tests/integration/ -v --tb=short

test-e2e:
	python -m pytest tests/e2e/ -v --tb=short

test-cov:
	python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# ── Linting ───────────────────────────────────────────────────────────────────

lint:
	python -m ruff check app/ --fix

lint-check:
	python -m ruff check app/

format:
	python -m ruff format app/

# ── Seed Data ──────────────────────────────────────────────────────────────────

seed:
	@echo "🌱 Populating database with test data..."
	python scripts/seed.py
	@echo "✅ Seed complete. Credenciales en scripts/seed.py"

# ── Build ──────────────────────────────────────────────────────────────────────

build:
	$(COMPOSE) -f docker-compose.prod.yml build --no-cache

build-nocache:
	$(COMPOSE) -f docker-compose.prod.yml build --pull --no-cache

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	$(COMPOSE) -f docker-compose.prod.yml down -v --rmi local
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml down -v --rmi local 2>/dev/null || true
	@echo "Cleanup complete."

restart:
	$(COMPOSE) -f docker-compose.prod.yml restart

restart-api:
	$(COMPOSE) -f docker-compose.prod.yml restart api

restart-celery:
	$(COMPOSE) -f docker-compose.prod.yml restart celery-worker celery-beat

# ── Health checks ─────────────────────────────────────────────────────────────

health:
	@echo "Checking service health..."
	@curl -sf http://localhost:8000/health/ready && echo "API: OK" || echo "API: FAIL"
	@$(COMPOSE) -f docker-compose.prod.yml exec -T postgres pg_isready -U inmuebles -d inmobiliaria_db && echo "Postgres: OK" || echo "Postgres: FAIL"
	@$(COMPOSE) -f docker-compose.prod.yml exec -T redis redis-cli ping && echo "Redis: OK" || echo "Redis: FAIL"

# ── Shell access ──────────────────────────────────────────────────────────────

shell-api:
	$(COMPOSE) -f docker-compose.prod.yml exec api /bin/sh

shell-postgres:
	$(COMPOSE) -f docker-compose.prod.yml exec postgres psql -U inmuebles -d inmobiliaria_db

shell-redis:
	$(COMPOSE) -f docker-compose.prod.yml exec redis redis-cli

# ── Database console ──────────────────────────────────────────────────────────

psql:
	$(COMPOSE) -f docker-compose.prod.yml exec postgres psql -U inmuebles -d inmobiliaria_db

# ── Celery ────────────────────────────────────────────────────────────────────

celery-flower:
	$(COMPOSE) -f docker-compose.prod.yml exec celery-worker celery -A app.core.celery_app flower --port=5555

# ── SSL / Let's Encrypt ────────────────────────────────────────────────────────

cert-init:
	@echo "Initializing Let's Encrypt certificate..."
	mkdir -p ./volumes/certbot/conf/live/inmobiliaria
	@echo "Place your certificate files in ./volumes/certbot/conf/live/inmobiliaria/"
	@echo "Or use certbot in standalone mode after stopping nginx:"
	@echo "  $(COMPOSE) -f docker-compose.prod.yml run --rm --entrypoint certbot certbot-auto certonly"

cert-renew:
	@echo "Renewing Let's Encrypt certificates..."
	$(COMPOSE) -f docker-compose.prod.yml run --rm --entrypoint certbot certbot-auto renew --webroot -w /var/www/certbot
	$(COMPOSE) -f docker-compose.prod.yml exec nginx nginx -s reload
