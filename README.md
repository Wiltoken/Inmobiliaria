# auth-login-platform

Hexagonal JWT authentication platform — FastAPI async + SQLAlchemy 2.0 + PostgreSQL 16 + Redis 7.

## Slices

- **Slice 1 — Foundation**: Project scaffold, Docker Compose, config, ORM models, Alembic migration, Redis client
- **Slice 2 — Core Security + Auth Endpoints** (forthcoming)
- **Slice 3 — Advanced Features + Admin** (forthcoming)
- **Slice 4 — Testing** (forthcoming)

## Quick Start

```bash
# 1. Copy and edit environment
cp .env.example .env
# Edit .env — set SECRET_KEY (required)

# 2. Start all services
docker compose up --build

# 3. Run migrations
docker compose exec api alembic upgrade head

# 4. Verify
curl http://localhost:8000/health/ready
open http://localhost:8000/docs
```

## Local Development (without Docker)

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

## Key Files

| Path | Purpose |
|------|---------|
| `app/config.py` | All pydantic-settings (zero hardcoded literals) |
| `app/domain/models.py` | SQLAlchemy 2.0 async ORM models (7 tables) |
| `app/adapters/redis_client.py` | Async Redis: blacklist, rate-limit, refresh, session |
| `migrations/versions/001_initial.py` | Alembic initial migration |
| `docker-compose.yml` | PostgreSQL 16 + Redis 7 + API service |
