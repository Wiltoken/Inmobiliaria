# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│   Web Browser (SPA) / Mobile App / Third-party Integrations                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ HTTPS (TLS 1.3)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NGINX REVERSE PROXY                               │
│   • SSL termination (Let's Encrypt)                                         │
│   • Rate limiting (30 req/s per IP)                                         │
│   • Static file serving                                                     │
│   • Security headers (CSP, X-Frame-Options, etc.)                           │
│   • WebSocket proxy support                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌──────────┐     ┌─────────────┐   ┌──────────┐
            │  /api/*  │     │  /docs/*   │   │ /static  │
            │  (fast)  │     │   (Swagger)│   │  (files) │
            └────┬─────┘     └──────┬──────┘   └──────────┘
                 │                 │
                 │                 │
                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│   │   API Replica 1  │  │   API Replica 2  │  │   API Replica N  │  (scaled)
│   │  (FastAPI/UVicorn)  │  │  (FastAPI/UVicorn)  │  │  (FastAPI/UVicorn)  │
│   └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                              │
│   • JWT Authentication (access + refresh tokens)                             │
│   • RBAC Authorization (buyer/seller/agent/admin)                           │
│   • Rate limiting (Redis token bucket)                                      │
│   • Audit logging (all auth events)                                         │
│   • Input validation (Pydantic)                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 ▼                   ▼                   ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   PgBouncer     │   │     Redis        │   │     MinIO       │
│  (connection     │   │  (sessions,     │   │  (S3-compatible  │
│   pooling)       │   │   cache, pub/sub)│   │   object store) │
│                  │   │                  │   │                  │
│  • Transaction   │   │  • JWT blacklist │   │  • Property      │
│    pooling      │   │  • Rate limits   │   │    photos        │
│  • 200 max      │   │  • Match cache   │   │  • User avatars  │
│    connections  │   │  • Celery borker │   │  • Static assets│
└────────┬─────────┘   └────────┬─────────┘   └──────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│    PostgreSQL     │   │    Celery        │
│    16 + PostGIS   │   │  Workers         │
│                   │   │                  │
│  • Users/Roles    │   │  • match_recompute│
│  • Properties     │   │  • daily_backup  │
│  • Matches        │   │  • cleanup       │
│  • Inquiries     │   │                  │
│  • Audit logs    │   │  Celery Beat     │
│                   │   │  (scheduler)    │
│  • GiST indexes  │   │                  │
│    for PostGIS   │   │  • Daily 2AM     │
│  • GIN trgm for  │   │    backup        │
│    full-text     │   │  • Every 6h      │
│                   │   │    cleanup      │
└──────────────────┘   └──────────────────┘
```

## Hexagonal Architecture

The platform follows **Hexagonal Architecture** (also known as Ports and Adapters) to maintain clean separation between business logic and infrastructure concerns.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DRIVING ADAPTERS                               │
│  (Primary/Input Ports)                                                      │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                        FastAPI Layer                                 │  │
│   │  • app/api/v1/*.py (endpoints)                                       │  │
│   │  • app/api/v1/deps.py (dependency injection)                         │  │
│   │  • app/main.py (application wiring)                                  │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             APPLICATION CORE                                │
│  (Domain + Application Services — pure Python, no framework dependencies)   │
│                                                                              │
│  ┌────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │      DOMAIN LAYER          │  │       APPLICATION LAYER            │   │
│  │                            │  │                                     │   │
│  │  • app/domain/models.py   │  │  • app/core/matching.py (use cases)│   │
│  │    (SQLAlchemy entities)  │  │  • app/core/security.py             │   │
│  │                            │  │  • app/core/exceptions.py           │   │
│  │  • app/domain/schemas.py  │  │  • app/core/celery_app.py (tasks)   │   │
│  │    (Pydantic DTOs)        │  │                                     │   │
│  │                            │  │                                     │   │
│  │  Domain Services:         │  │  Ports (interfaces):                │   │
│  │  • Property listing        │  │  • app/ports/captcha.py            │   │
│  │  • Match computation      │  │                                     │   │
│  │  • Inquiry handling       │  │                                     │   │
│  └────────────────────────────┘  └─────────────────────────────────────┘   │
│                                                                              │
│  ENTITIES: User, Property, BuyerProfile, SellerProfile, AgentProfile,        │
│            Match, Inquiry, Favorite, AuditLog                                │
│                                                                              │
│  VALUE OBJECTS: PropertyType, PropertyOperation, PropertyStatus,             │
│                 ContactPreference, InquiryStatus                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DRIVEN ADAPTERS                                  │
│  (Secondary/Output Ports)                                                    │
│                                                                              │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│   │  Database       │  │  Redis          │  │  S3/MinIO       │             │
│   │  Adapter       │  │  Adapter        │  │  Adapter        │             │
│   │                 │  │                 │  │                 │             │
│   │ app/adapters/  │  │ app/adapters/   │  │ app/adapters/   │             │
│   │ database.py     │  │ redis_client.py │  │ s3_storage.py   │             │
│   │                 │  │                 │  │                 │             │
│   │ • SQLAlchemy    │  │ • Connection    │  │ • boto3 client  │             │
│   │ • asyncpg       │  │   pooling      │  │ • Multipart     │             │
│   │ • Alembic       │  │ • Token bucket │  │   upload        │             │
│   │   migrations   │  │ • Pub/sub      │  │ • Presigned     │             │
│   │                 │  │                 │  │   URLs          │             │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
│   ┌─────────────────┐  ┌─────────────────┐                                 │
│   │  reCAPTCHA      │  │  SMTP           │                                 │
│   │  Adapter        │  │  Adapter        │                                 │
│   │                 │  │                 │                                 │
│   │ app/adapters/   │  │ (aiosmtplib)    │                                 │
│   │ google_recaptcha│  │                 │                                 │
│   │                 │  │ • Password reset│                                 │
│   │ • Score verify  │  │ • Notifications │                                 │
│   └─────────────────┘  └─────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Dependency Inversion**: Core domain never imports infrastructure. Interfaces (ports) are defined in `app/ports/`, implementations (adapters) in `app/adapters/`.

2. **Single Responsibility**: Each adapter handles one external concern (database, cache, storage, etc.)

3. **Testability**: Core business logic is framework-agnostic and can be unit tested without external dependencies.

4. **Async-First**: All I/O operations use `async/await` for maximum throughput.

## Tech Stack Rationale

### FastAPI (async web framework)
- **Why**: Native `async/await` support enables high concurrency without threading complexity. Built-in Pydantic validation eliminates boilerplate. OpenAPI auto-generation from type hints.
- **Alternative considered**: Flask (synchronous only, requires explicit async), Django (heavy, opinionated ORM)

### PostgreSQL 16 + PostGIS
- **Why**: PostGIS provides geospatial queries (within radius, distance calculations) critical for location-based property matching. JSONB enables flexible metadata without schema changes.
- **Alternative considered**: MongoDB (weaker geospatial, no GIS extension), MySQL (inferior GIS support)

### Redis 7
- **Why**: Sub-millisecond latency for token blacklisting and rate limiting. Pub/sub for real-time notifications. Native sorted set support for token bucket algorithm. Celery broker.
- **Alternative considered**: Memcached (no pub/sub, no sorted sets), in-memory (no persistence, no distribution)

### SQLAlchemy 2.0 (async)
- **Why**: Type-safe ORM with native async support via `asyncpg`. Declarative base enables Alembic migration generation. Hybrid properties for computed fields.
- **Alternative considered**: Raw asyncpg (no ORM abstraction), SQLModel (less mature async support)

### MinIO (S3-compatible)
- **Why**: Drop-in S3 API enables easy migration to AWS S3 in production. Self-hosted for cost control in staging/dev. EC2 metadata for credentials.
- **Alternative considered**: Local filesystem (no CDN integration), Azure Blob (vendor lock-in)

## Domain Model

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │       │    Role     │       │  AuditLog   │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◆─────▶│ id (PK)     │◀─◆────│ id (PK)     │
│ tenant_id   │       │ name        │       │ user_id(FK) │
│ username    │       └─────────────┘       │ action      │
│ email       │                              │ ip_address  │
│ password_hash       ┌─────────────┐         │ created_at  │
│ is_active   │       │  Buyer     │         └─────────────┘
│ is_locked   │       │  Profile   │
│ created_at  │       ├─────────────┤
└──────┬──────┘       │ id (PK)     │
       │              │ user_id(FK) │◆────▶ User
       │              │ budget_min   │       (one-to-one)
       │              │ budget_max   │
       │              │ locations[]  │
       │              │ features[]   │
       │              │ types[]      │
       │              └───────┬──────┘
       │                      │
       │              ┌───────┴──────┐
       │              │              │
       │              ▼              │
┌──────┴──────┐  ┌───────┴────┐   │
│   Seller     │  │   Match    │   │
│   Profile   │  ├────────────┤   │
├─────────────┤  │ id (PK)    │   │
│ id (PK)     │  │ buyer_id(FK)│◀──┘
│ user_id(FK) │◆─▶│ property_id│──▶┌─────────────┐
│ phone       │  │ score      │   │  Property   │
│ company_name│  │ breakdown  │   ├─────────────┤
└─────────────┘  │ computed_at│   │ id (PK)     │
                  └────────────┘   │ type        │
       ┌─────────────┐             │ operation   │
       │   Agent     │             │ status      │
       │   Profile   │             │ price       │
       ├─────────────┤             │ location    │
       │ id (PK)     │             │ features    │
       │ user_id(FK) │              │ owner_id    │
       │ license_num │              │ agent_id    │
       │ agency_name │              │ photos[]    │
       └─────────────┘              │ favorites[] │
                                    │ inquiries[] │
       ┌─────────────┐              └──────┬──────┘
       │  Favorite   │                     │
       ├─────────────┤                     │
       │ id (PK)     │                     │
       │ user_id(FK) │◆──────┐              │
       │ property_id│───────▶Property       │
       │ created_at  │                     │
       └─────────────┘                     │
                                           │
       ┌─────────────┐                     │
       │  Inquiry    │                     │
       ├─────────────┤                     │
       │ id (PK)     │                     │
       │ from_user_id│                     │
       │ to_user_id  │                     │
       │ property_id│◀────────────────────┘
       │ message    │
       │ status     │
       │ response   │
       └─────────────┘
```

### Core Entities

| Entity | Purpose | Key Attributes |
|--------|---------|----------------|
| `User` | Authenticated user with multi-role support | email, password_hash, is_locked, roles[] |
| `BuyerProfile` | Buyer preferences for matching | budget_min/max, preferred_locations[], features[], types[] |
| `SellerProfile` | Seller contact information | phone, company_name |
| `AgentProfile` | Licensed real estate agent | license_number, agency_name |
| `Property` | Real estate listing with geospatial data | type, operation, status, price, location (GeoJSON), features, photos[] |
| `PropertyPhoto` | Photos for a property listing | url, s3_key, order |
| `Match` | Computed buyer-property match score | buyer_id, property_id, score, breakdown |
| `Inquiry` | User inquiry about a property | from_user, to_user, property, message, status |
| `Favorite` | User's favorited properties | user_id, property_id |
| `AuditLog` | Immutable auth event log | user_id, action, ip_address, details, created_at |

## Matching Algorithm

The matching algorithm computes a weighted similarity score between a buyer's preferences and a property's attributes.

### Scoring Weights

| Factor | Weight | Scoring Method |
|--------|--------|----------------|
| Price | 30% | 100 if within budget_min/max, linear decay outside |
| Location | 25% | 100 if within preferred radius, decay based on haversine distance |
| Features | 25% | Jaccard similarity: intersection/union of feature sets |
| Area | 20% | 100 if within area_min/max, linear decay outside |

### Score Computation

```python
def compute_match(buyer: BuyerProfile, prop: Property) -> dict:
    price_score = score_price(buyer.budget_min, buyer.budget_max, prop.price)
    location_score = score_location(buyer.preferred_locations, prop.lat, prop.lon)
    features_score = score_features(buyer.features, prop.features)
    area_score = score_area(buyer.area_min, buyer.area_max, prop.area_m2)

    total = (
        price_score * 0.30 +
        location_score * 0.25 +
        features_score * 0.25 +
        area_score * 0.20
    )

    return {"total": round(total, 2), "breakdown": {...}}
```

### Cache Strategy

- Results cached in Redis with key `match:{buyer_id}`
- TTL: 1 hour (configurable via `MATCH_CACHE_TTL_SECONDS`)
- Cache invalidated on buyer profile update or property change
- Celery task `match_recompute` runs daily at 3 AM UTC

## Decision Records (ADRs)

### ADR-001: Async-First Architecture
**Status**: Accepted
**Context**: High concurrent user load expected for property search and matching.
**Decision**: All I/O operations use async/await. SQLAlchemy 2.0 async, asyncpg, redis.asyncio.
**Consequences**: Better throughput under load; requires Python 3.13+ for optimal performance.

### ADR-002: PostgreSQL + PostGIS for Geospatial
**Status**: Accepted
**Context**: Location-based property search is a core feature.
**Decision**: Use PostGIS extension for geospatial queries (ST_DWithin, ST_Distance).
**Consequences**: Requires PostGIS-enabled PostgreSQL image; more complex migrations.

### ADR-003: Redis for Rate Limiting
**Status**: Accepted
**Context**: Token bucket rate limiting needs sub-millisecond latency.
**Decision**: Redis sorted sets with timestamp scores for sliding window rate limiting.
**Consequences**: Additional infrastructure dependency; Redis must be highly available.

### ADR-004: JWT with Refresh Token Rotation
**Status**: Accepted
**Context**: Secure authentication with session invalidation support.
**Decision**: Short-lived access tokens (15 min) + long-lived refresh tokens (7 days) with rotation.
**Consequences**: Refresh tokens stored in both DB and Redis for fast validation.

### ADR-005: Celery + Redis for Background Tasks
**Status**: Accepted
**Context**: Async task queue for heavy operations (match computation, backups).
**Decision**: Celery with Redis broker and result backend.
**Consequences**: Additional complexity; requires beat scheduler for periodic tasks.

### ADR-006: YAML Config Layer (Optional)
**Status**: Accepted (Deferred)
**Context**: Environment-specific configuration management.
**Decision**: YAML config loader optional; primary config via environment variables.
**Consequences**: Environment variables are required; YAML provides convenience overrides.
