# Deployment Guide

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | 24.0+ | Required for container management |
| docker compose | v2.0+ | Required for orchestration (built into Docker) |
| Git | any | For cloning the repository |
| Domain name | - | For SSL certificates (optional for staging) |

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/your-org/inmobiliaria.git
cd inmobiliaria

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Generate Secrets

```bash
# Generate a secure SECRET_KEY (64+ characters)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Add to .env:
# SECRET_KEY=your_generated_key_here

# Generate MinIO credentials
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Start Production Environment

```bash
# Build and start all services
make prod

# Or directly with docker compose
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Run Migrations

```bash
make migrate
```

### 5. Create Admin User

```bash
# Access the API container
docker compose -f docker-compose.prod.yml exec api /bin/sh

# Create admin user via Python
python -c "
import asyncio
from app.adapters.database import get_engine, AsyncSession
from app.domain.models import User, Role
from app.core.security import hash_password
from sqlalchemy import select

async def create_admin():
    engine = get_engine()
    async with AsyncSession(engine) as session:
        # Create admin role if not exists
        result = await session.execute(select(Role).where(Role.name == 'admin'))
        admin_role = result.scalar_one_or_none()
        if not admin_role:
            admin_role = Role(name='admin')
            session.add(admin_role)
            await session.flush()
        
        # Create admin user
        admin = User(
            email='admin@example.com',
            username='admin',
            password_hash=hash_password('ChangeMe123!'),
            is_active=True,
            roles=[admin_role]
        )
        session.add(admin)
        await session.commit()
        print('Admin user created')

asyncio.run(create_admin())
"
```

### 6. Verify Deployment

```bash
# Check service health
make health

# Expected output:
# API: OK
# Postgres: OK
# Redis: OK

# View logs
make logs
```

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (64+ chars) | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_PASSWORD` | `changeme` | PostgreSQL password |
| `DATABASE_URL` | auto | Full connection string (override if needed) |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery broker URL |

### S3/MinIO

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT_URL` | `http://minio:9000` | S3 endpoint |
| `S3_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `S3_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `S3_BUCKET_NAME` | `inmobiliaria-photos` | Bucket name |
| `S3_REGION` | `us-east-1` | AWS region |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_LOGIN_ATTEMPTS` | `3` | Failed attempts before lockout |
| `LOCKOUT_DURATION_MINUTES` | `15` | Lockout duration |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `PASSWORD_MIN_LENGTH` | `8` | Minimum password length |
| `PASSWORD_EXPIRY_DAYS` | `30` | Password expiry (0=never) |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment (production) |
| `LOG_LEVEL` | `INFO` | Logging level |

### Compliance

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIT_RETENTION_DAYS` | `365` | Audit log retention (Ley 1581) |

## SSL Setup

### Option 1: Let's Encrypt (Recommended for Production)

```bash
# 1. Stop nginx
docker compose -f docker-compose.prod.yml stop nginx

# 2. Create certbot container (one-time)
docker compose -f docker-compose.prod.yml run --rm --entrypoint certbot certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d inmobiliaria.example.com \
  --email admin@example.com \
  --agree-tos \
  --non-interactive

# 3. Start nginx
docker compose -f docker-compose.prod.yml start nginx
```

### Option 2: Self-Signed (Development/Staging)

Self-signed certificates are automatically generated for `localhost` and `inmobiliaria.local`.

For production, replace the placeholder in `nginx/conf.d/inmobiliaria.conf`:

```nginx
ssl_certificate /etc/letsencrypt/live/inmobiliaria/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/inmobiliaria/privkey.pem;
```

### Certificate Renewal

```bash
# Add to crontab
0 0 * * * docker compose -f /path/to/docker-compose.prod.yml run --rm certbot certbot renew --webroot -w /var/www/certbot && docker compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload
```

## Database Migrations

### Run Migrations

```bash
# Apply all migrations
make migrate

# Or directly
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Create New Migration

```bash
# After model changes
docker compose -f docker-compose.prod.yml exec api alembic revision --autogenerate -m "Add property features index"

# Or with Make
make migrate-create
```

### Migration Rollback

```bash
# Rollback last migration
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1

# Rollback to specific revision
docker compose -f docker-compose.prod.yml exec api alembic downgrade <revision>
```

## First-Time Setup

### 1. Create Initial Roles

```bash
docker compose -f docker-compose.prod.yml exec api python -c "
import asyncio
from app.adapters.database import get_engine, AsyncSession
from app.domain.models import Role

async def create_roles():
    engine = get_engine()
    async with AsyncSession(engine) as session:
        for name in ['admin', 'buyer', 'seller', 'agent']:
            role = Role(name=name)
            session.add(role)
        await session.commit()
        print('Roles created')

asyncio.run(create_roles())
"
```

### 2. Verify MinIO Bucket

```bash
# Check bucket creation
docker compose -f docker-compose.prod.yml logs minio-create-bucket

# Access MinIO console at http://localhost:9001
# Default credentials: minioadmin / minioadmin
```

### 3. Health Check Verification

```bash
# Test all health endpoints
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/health/ready
# {"status":"ready"}

# Test through nginx
curl https://localhost/health
# {"status":"ok"}
```

## Docker Compose Commands

### Start Services

```bash
# Start in detached mode
docker compose -f docker-compose.prod.yml up -d

# Start with rebuild
docker compose -f docker-compose.prod.yml up -d --build

# Scale API replicas
docker compose -f docker-compose.prod.yml up -d --scale api=3
```

### Stop Services

```bash
# Stop without removing volumes
docker compose -f docker-compose.prod.yml stop

# Stop and remove containers
docker compose -f docker-compose.prod.yml down

# Stop and remove everything (including volumes!)
docker compose -f docker-compose.prod.yml down -v
```

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f postgres

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Restart Services

```bash
# Restart all
make restart

# Restart specific service
make restart-api
make restart-celery
```

## Production Checklist

- [ ] Set `SECRET_KEY` to a secure 64+ character value
- [ ] Change `POSTGRES_PASSWORD` from default
- [ ] Change MinIO credentials from default
- [ ] Configure `APP_ENV=production`
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Configure SSL certificates (Let's Encrypt)
- [ ] Run database migrations
- [ ] Create admin user
- [ ] Verify health endpoints
- [ ] Set up backup schedule
- [ ] Configure monitoring/alerting
- [ ] Review rate limiting configuration
- [ ] Enable reCAPTCHA for production

## Troubleshooting

### API Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs api

# Common issues:
# - Missing SECRET_KEY in .env
# - Database not ready (wait for postgres health)
# - Port 8000 already in use
```

### Database Connection Issues

```bash
# Check postgres is healthy
docker compose -f docker-compose.prod.yml ps postgres

# Test connection
docker compose -f docker-compose.prod.yml exec api python -c "
import asyncio
from app.adapters.database import get_engine
async def test():
    engine = get_engine()
    async with engine.connect() as conn:
        print(await conn.execute(__import__('sqlalchemy').text('SELECT 1')))
asyncio.run(test())
"
```

### Redis Connection Issues

```bash
# Check redis is healthy
docker compose -f docker-compose.prod.yml ps redis

# Test connection
docker compose -f docker-compose.prod.yml exec api python -c "
import asyncio
from app.adapters.redis_client import get_redis_client
async def test():
    r = get_redis_client()
    await r.ping()
    print('Redis OK')
asyncio.run(test())
"
```

### Migration Failures

```bash
# Check current migration state
docker compose -f docker-compose.prod.yml exec api alembic current

# Check migration history
docker compose -f docker-compose.prod.yml exec api alembic history

# Force stamp current version
docker compose -f docker-compose.prod.yml exec api alembic stamp head
```
