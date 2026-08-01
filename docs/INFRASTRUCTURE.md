# Infrastructure

## Production Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOAD BALANCER / CDN                               │
│                    (CloudFlare / AWS CloudFront)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ HTTPS
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS EC2 / ECS                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    Docker Swarm / Kubernetes                         │     │
│  │                                                                      │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │     │
│  │  │   Nginx     │  │   Nginx     │  │   Nginx     │  (scaled)       │     │
│  │  │   (LB)      │  │   (LB)      │  │   (LB)      │                 │     │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │     │
│  │         │                 │                 │                         │     │
│  │         └─────────────────┼─────────────────┘                         │     │
│  │                           │                                           │     │
│  │                           ▼                                           │     │
│  │         ┌─────────────────────────────────────┐                       │     │
│  │         │         Internal Network            │                       │     │
│  │         │                                     │                       │     │
│  │         │  ┌──────────┐  ┌──────────┐        │                       │     │
│  │         │  │  API     │  │  API     │  ...   │  (replicated)         │     │
│  │         │  │  (uvicorn)│  │  (uvicorn)│        │                       │     │
│  │         │  └────┬─────┘  └────┬─────┘        │                       │     │
│  │         │       │             │              │                       │     │
│  │         │       └──────┬──────┘              │                       │     │
│  │         │              │                      │                       │     │
│  │         │              ▼                      │                       │     │
│  │         │  ┌───────────────────────┐          │                       │     │
│  │         │  │      PgBouncer        │          │                       │     │
│  │         │  │  (Connection Pooler) │          │                       │     │
│  │         │  └───────────┬───────────┘          │                       │     │
│  │         │              │                        │                       │     │
│  │         │   ┌─────────┴─────────┐            │                       │     │
│  │         │   │                     │            │                       │     │
│  │         │   ▼                     ▼            │                       │     │
│  │         │ ┌──────┐  ┌─────────┐ ┌──────┐      │                       │     │
│  │         │ │ Redis│  │Postgres │ │MinIO │      │                       │     │
│  │         │ │ 7    │  │ 16+PGIS │ │ S3   │      │                       │     │
│  │         │ └──────┘  └─────────┘ └──────┘      │                       │     │
│  │         │                                     │                       │     │
│  │         │  ┌──────────┐  ┌──────────┐        │                       │     │
│  │         │  │ Celery   │  │ Celery   │        │                       │     │
│  │         │  │ Worker   │  │ Beat     │        │                       │     │
│  │         │  └──────────┘  └──────────┘        │                       │     │
│  │         └─────────────────────────────────────┘                       │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Descriptions

### Nginx (Reverse Proxy & Load Balancer)

| Aspect | Details |
|--------|---------|
| **Image** | `nginx:alpine` |
| **Ports** | 80 (HTTP), 443 (HTTPS) |
| **Scaling** | Multiple replicas behind load balancer |
| **Purpose** | SSL termination, rate limiting, static file serving, security headers |
| **Configuration** | `/nginx/nginx.conf`, `/nginx/conf.d/inmobiliaria.conf` |

**Key configurations:**
- Worker processes: auto (match CPU cores)
- Worker connections: 2048
- Gzip compression enabled
- Client max body size: 20MB
- Rate limiting zones: 30 req/s per IP (general), 30 req/s (API), 5 req/s (auth)

### API Service (FastAPI Application)

| Aspect | Details |
|--------|---------|
| **Image** | Built from `Dockerfile` |
| **Scaling** | 2 replicas default, 3+ for production |
| **Health Check** | `GET /health/ready` |
| **Dependencies** | PostgreSQL (via PgBouncer), Redis, MinIO |
| **Replicas** | Configurable via `--scale api=N` |

**Environment variables:**
```bash
DATABASE_URL=postgresql+asyncpg://inmuebles:${POSTGRES_PASSWORD}@pgbouncer:6432/inmobiliaria_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
SECRET_KEY=<64-char-secret>
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=${MINIO_ROOT_USER}
S3_SECRET_KEY=${MINIO_ROOT_PASSWORD}
S3_BUCKET_NAME=inmobiliaria-photos
```

### PgBouncer (Connection Pooler)

| Aspect | Details |
|--------|---------|
| **Image** | `edoburu/pgbouncer:latest` |
| **Port** | 6432 |
| **Pool Mode** | Transaction |
| **Max Client Connections** | 200 |
| **Default Pool Size** | 25 |
| **Purpose** | Reduce PostgreSQL connection overhead |

**Why transaction pooling?**
- PostgreSQL connection overhead: ~5-10ms per connection
- Async applications open/close connections rapidly
- Transaction pooling allows thousands of logical connections with ~25 actual connections
- Works well with asyncpg's connection pool

### PostgreSQL 16 + PostGIS

| Aspect | Details |
|--------|---------|
| **Image** | `postgis/postgis:16-3.4-alpine` |
| **Port** | 5432 |
| **Volume** | `pgdata:/var/lib/postgresql/data` |
| **Extensions** | PostGIS 3.4, pg_trgm, UUID-ossp |
| **Backup** | `/backups` volume mounted |
| **Health Check** | `pg_isready -U inmuebles -d inmobiliaria_db` |

**Key features:**
- GiST index on `location` column for geospatial queries
- GIN index with `gin_trgm_ops` for full-text search on title/description
- BRIN index on `audit_logs.created_at` for time-series queries
- UUID primary keys generated with `uuid_generate_v4()`

### Redis 7

| Aspect | Details |
|--------|---------|
| **Image** | `redis:7-alpine` |
| **Port** | 6379 |
| **Volume** | `redisdata:/data` |
| **Memory** | 256MB max, `allkeys-lru` eviction |
| **Persistence** | AOF (appendonly yes) |
| **Health Check** | `redis-cli ping` |

**Key uses:**
- JWT access token blacklist (TTL = access token lifetime)
- Refresh token storage (TTL = refresh token lifetime)
- Rate limiting counters (sliding window, 1 second)
- Match result cache (TTL = 1 hour)
- Celery broker and result backend
- Last-active timestamps for session tracking

### MinIO (S3-Compatible Object Storage)

| Aspect | Details |
|--------|---------|
| **Image** | `minio/minio:latest` |
| **Ports** | 9000 (API), 9001 (Console) |
| **Volume** | `miniodata:/data` |
| **Health Check** | `GET /minio/health/live` |
| **Buckets** | `inmobiliaria-photos` |

**Key uses:**
- Property photos storage
- User avatars
- Static assets (via presigned URLs)
- Migration to AWS S3 in production via endpoint change

### Celery Workers

| Aspect | Details |
|--------|---------|
| **Image** | Built from `Dockerfile` |
| **Broker** | Redis (db/1) |
| **Result Backend** | Redis (db/0) |
| **Concurrency** | 4 workers per instance |
| **Queues** | `celery` (default), `matching`, `maintenance` |

**Periodic tasks:**
| Task | Schedule | Queue |
|------|----------|-------|
| `daily_backup` | Daily 2:00 AM UTC | maintenance |
| `cleanup_old_matches` | Every 6 hours | maintenance |
| `match_recompute` | Daily 3:00 AM UTC | matching |
| `cleanup_expired_tokens` | Every hour | maintenance |

### Celery Beat (Scheduler)

| Aspect | Details |
|--------|---------|
| **Image** | Built from `Dockerfile` |
| **Purpose** | Schedule periodic tasks |
| **Config** | `app/core/celery_app.py` |

## Scaling Strategy

### Horizontal API Scaling

```
                     ┌─────────────────────┐
                     │   Nginx (1 or 2)   │
                     │   Load Balancer     │
                     └──────────┬──────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
     │  API Pod 1  │     │  API Pod 2  │     │  API Pod N  │
     │ (uvicorn)   │     │ (uvicorn)   │     │ (uvicorn)   │
     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
     │  PgBouncer  │     │   Redis     │     │   MinIO     │
     │  (1 inst)  │     │  (Cluster)  │     │  (1 inst)   │
     └──────┬──────┘     └──────┬──────┘     └─────────────┘
            │                   │
            ▼                   ▼
     ┌─────────────┐     ┌─────────────┐
     │ PostgreSQL  │     │ PostgreSQL  │
     │  Primary    │────▶│  Replica    │
     └─────────────┘     └─────────────┘
```

### Read Replica Strategy

For read-heavy workloads (property search):
1. Add PostgreSQL read replica(s)
2. Route `SELECT` queries to replica
3. Route `INSERT/UPDATE/DELETE` to primary
4. PgBouncer can be configured with multiple backends

### Redis Cluster (Future)

For high availability:
1. Redis Sentinel for automatic failover
2. 1 primary + 2 replicas
3. Sentinel monitors primary health
4. Clients automatically reconnect to new primary

## Resource Requirements

### Development / Minimal Production

| Service | CPU | Memory | Disk |
|---------|-----|--------|------|
| API | 0.5 cores | 512 MB | - |
| PostgreSQL | 1 core | 1 GB | 10 GB |
| Redis | 0.25 cores | 128 MB | 1 GB |
| MinIO | 0.5 cores | 512 MB | 10 GB |

### Standard Production

| Service | CPU | Memory | Disk |
|---------|-----|--------|------|
| API (per replica) | 1 core | 1 GB | - |
| API (3 replicas) | 3 cores | 3 GB | - |
| PgBouncer | 0.25 cores | 256 MB | - |
| PostgreSQL | 2 cores | 4 GB | 50 GB |
| Redis | 1 core | 512 MB | 2 GB |
| MinIO | 1 core | 2 GB | 100 GB |
| Celery Worker | 1 core | 512 MB | - |
| Celery Beat | 0.25 cores | 256 MB | - |
| Nginx | 0.5 cores | 256 MB | - |

### High Availability Production

| Service | CPU | Memory | Disk |
|---------|-----|--------|------|
| API (per replica) | 1 core | 1 GB | - |
| API (5 replicas) | 5 cores | 5 GB | - |
| PgBouncer (2x) | 0.5 cores | 512 MB | - |
| PostgreSQL Primary | 4 cores | 8 GB | 100 GB |
| PostgreSQL Replica (2x) | 4 cores | 8 GB | 100 GB |
| Redis Sentinel (3x) | 0.5 cores | 256 MB | 2 GB |
| MinIO (4-node) | 2 cores | 4 GB | 200 GB |
| Celery Worker (2x) | 2 cores | 1 GB | - |

## Network Configuration

```yaml
# docker-compose.prod.yml networks (implicit)
networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

**Service communication:**
- `api` → `pgbouncer:6432` → `postgres:5432`
- `api` → `redis:6379`
- `api` → `minio:9000`
- `celery-worker` → `redis:6379`, `postgres:5432`
- `nginx` → `api:8000`

## Backup Strategy

1. **Daily automated backups** via Celery (`daily_backup` task)
   - Runs at 2:00 AM UTC
   - pg_dump to plain SQL format
   - gzip compression (level 9)
   - Stored in `/backups` volume
   - 7-day retention

2. **Pre-restore safety backup**
   - Automatic before any restore operation
   - Timestamped filename

3. **Offsite backup (production)**
   - Sync `/backups` to S3/Cloud Storage daily
   - Cross-region replication for DR

## Monitoring

### Health Endpoints

| Endpoint | Purpose | Auth Required |
|----------|---------|--------------|
| `GET /health` | Liveness probe | No |
| `GET /health/ready` | Readiness probe (DB + Redis) | No |

### Metrics to Monitor

- API: request latency (p50, p95, p99), error rate, replica count
- PgBouncer: client connections, server connections, wait time
- PostgreSQL: connections, queries/sec, replication lag, disk I/O
- Redis: memory usage, hit rate, key count
- Celery: task success/failure rate, queue depth, worker count
