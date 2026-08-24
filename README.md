# Inmobiliaria Platform

Plataforma inmobiliaria para compradores, vendedores y agentes — FastAPI + React + PostgreSQL/PostGIS.

---

## 🔐 Accesos (Repo Privado)

### Frontend

| Entorno | URL |
|---------|-----|
| Local | http://localhost:3000 |
| Remoto (túnel) | https://inmobiliaria-demo.loca.lt |

### Backend API

| Entorno | URL |
|---------|-----|
| Local | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Remoto (túnel) | https://inmobiliaria-api.loca.lt |
| Swagger Remoto | https://inmobiliaria-api.loca.lt/docs |

### Servicios de Infraestructura

| Servicio | URL | Usuario / Contraseña |
|----------|-----|---------------------|
| PostgreSQL | localhost:5432 | `inmuebles` / `changeme` |
| Redis | localhost:6379 | (sin contraseña) |
| MinIO Console | http://localhost:9001 | `minioadmin` / `minioadmin` |
| MinIO API (S3) | http://localhost:9000 | `minioadmin` / `minioadmin` |

### Credenciales de Usuarios

| Rol | Usuario | Email | Contraseña |
|-----|---------|-------|------------|
| **Super Admin** | `admin` | admin@inmobiliaria.com | `Admin123!` |
| **Agent** | `agent1` | agent1@inmobiliaria.com | `Agent123!` |
| **Agent** | `agent2` | agent2@inmobiliaria.com | `Agent123!` |
| **Agent** | `agent3` | agent3@inmobiliaria.com | `Agent123!` |
| **Seller** | `seller1` | seller1@inmobiliaria.com | `Seller123!` |
| **Seller** | `seller2` | seller2@inmobiliaria.com | `Seller123!` |
| **Seller** | `seller3` | seller3@inmobiliaria.com | `Seller123!` |
| **Seller** | `seller4` | seller4@inmobiliaria.com | `Seller123!` |
| **Seller** | `seller5` | seller5@inmobiliaria.com | `Seller123!` |
| **Buyer** | `buyer1` | buyer1@inmobiliaria.com | `Buyer123!` |
| **Buyer** | `buyer2` | buyer2@inmobiliaria.com | `Buyer123!` |
| **Buyer** | `buyer3` | buyer3@inmobiliaria.com | `Buyer123!` |

> ⚠️ Estos usuarios se crean ejecutando `python scripts/seed.py` contra la base de datos.

### GitHub

| Dato | Valor |
|------|-------|
| Repo | https://github.com/Wiltoken/Inmobiliaria (privado) |
| SSH | `git@github.com:Wiltoken/Inmobiliaria.git` |
| Branch principal | `main` |
| Branch activa | `feat/etapa-2-infra` |

---

## Quick Start

```bash
# 1. Clonar
git clone git@github.com:Wiltoken/Inmobiliaria.git
cd Inmobiliaria

# 2. Levantar servicios
docker compose up -d

# 3. Correr seed (usuarios de prueba)
python scripts/seed.py

# 4. Frontend
cd frontend && npm install && npm run dev
```

**Accesos locales:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- MinIO: http://localhost:9001

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

Full architecture documentation: [Documentación Inmobiliaria/ARCHITECTURE.md](Documentación%20Inmobiliaria/ARCHITECTURE.md)

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
| [Architecture](Documentación%20Inmobiliaria/ARCHITECTURE.md) | System design, domain model, ADRs |
| [Infrastructure](Documentación%20Inmobiliaria/INFRASTRUCTURE.md) | Service details, scaling, networking |
| [API Reference](Documentación%20Inmobiliaria/API.md) | All endpoints, request/response examples |
| [Deployment](Documentación%20Inmobiliaria/DEPLOYMENT.md) | Production setup, SSL, migrations |
| [Security](Documentación%20Inmobiliaria/SECURITY.md) | Auth flow, RBAC, rate limiting, OWASP |
| [Development](Documentación%20Inmobiliaria/DEVELOPMENT.md) | Local setup, testing, code style |
| [Operations](Documentación%20Inmobiliaria/OPERATIONS.md) | Runbooks, monitoring, backups |

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

Documentación Inmobiliaria/  # Documentación completa
scripts/              # Backup, restore scripts
nginx/                # Nginx configuration
pgbouncer/            # Connection pooler config
```

## License

MIT
