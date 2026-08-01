# Inmobiliaria Platform

A production-grade real estate platform built with FastAPI, PostgreSQL/PostGIS, Redis, and Celery.

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/your-org/inmobiliaria.git
cd inmobiliaria
cp .env.example .env
# Edit .env — set SECRET_KEY (required)

# 2. Start production environment
make prod

# 3. Run migrations
make migrate

# 4. Create admin user (see docs/DEPLOYMENT.md)
```

**Access:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx (SSL)                              │
│                    Rate Limit | Security Headers                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐            ┌────▼────┐            ┌────▼────┐
   │  API    │            │  API    │            │  API    │
   │ (FastAPI)│            │ (FastAPI)│            │ (FastAPI)│
   └────┬────┘            └────┬────┘            └────┬────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
   ┌───────────┐      ┌────────┴───────┐      ┌───────────┐
   │ PgBouncer │      │     Redis      │      │   MinIO   │
   │  (pool)   │      │  (cache/broker)│      │  (S3 API) │
   └─────┬─────┘      └────────────────┘      └───────────┘
         │
    ┌────▼────┐
    │PostgreSQL│
    │ +PostGIS│
    └─────────┘
```

Full architecture documentation: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| API | FastAPI + Uvicorn | Async REST API |
| Database | PostgreSQL 16 + PostGIS | Primary data store |
| Cache | Redis 7 | Sessions, rate limiting, cache |
| Queue | Celery + Redis | Background tasks |
| Storage | MinIO (S3-compatible) | Property photos, static files |
| Proxy | Nginx + PgBouncer | Load balancing, connection pooling |

## Features

- **Authentication**: JWT with refresh token rotation, account lockout, audit logging
- **RBAC**: Role-based access (admin, agent, seller, buyer)
- **Property Management**: CRUD, geospatial search, photo upload
- **Matching Algorithm**: Weighted scoring (price, location, features, area)
- **Inquiries**: Buyer-seller communication with status tracking
- **Rate Limiting**: Layered (nginx + Redis token bucket)
- **Compliance**: Colombian Ley 1581 data protection ready

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, domain model, ADRs |
| [Infrastructure](docs/INFRASTRUCTURE.md) | Service details, scaling, networking |
| [API Reference](docs/API.md) | All endpoints, request/response examples |
| [Deployment](docs/DEPLOYMENT.md) | Production setup, SSL, migrations |
| [Security](docs/SECURITY.md) | Auth flow, RBAC, rate limiting, OWASP |
| [Development](docs/DEVELOPMENT.md) | Local setup, testing, code style |
| [Operations](docs/OPERATIONS.md) | Runbooks, monitoring, backups |

## Commands

```bash
# Development
make dev              # Start development environment (hot reload)
make test            # Run all tests
make lint            # Run linting + formatting

# Production
make prod            # Start production environment
make deploy          # Deploy with 3 API replicas
make logs            # View logs
make logs-api        # API logs only

# Maintenance
make migrate         # Run database migrations
make backup          # Create database backup
make restore         # Restore from backup
make health          # Check all services
```

Full command reference: `make help`

## Environment Variables

Key variables (see `.env.example` for full list):

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | JWT signing key (64+ chars) |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `MINIO_ROOT_USER` | Yes | MinIO access key |
| `MINIO_ROOT_PASSWORD` | Yes | MinIO secret key |

## Project Structure

```
app/
├── api/v1/           # FastAPI endpoints
├── core/             # Business logic, security, matching
├── domain/           # ORM models, Pydantic schemas
├── ports/            # Interface definitions
└── adapters/         # Database, Redis, S3 implementations

docs/                 # Architecture, deployment, API docs
scripts/              # Backup, restore scripts
nginx/                # Nginx configuration
pgbouncer/            # Connection pooler config
```

## License

MIT
