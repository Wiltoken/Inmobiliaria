# Design: Inmobiliaria Real Estate Matching Platform

## Technical Approach

Copy `auth-login-platform` hex foundation (FastAPI async, SQLAlchemy 2.0, PostgreSQL 16, Redis 7) as base. Extend with new domain modules: profiles, properties, matching engine, inquiries, and agent dashboard. Preserve existing middleware stack (CORS → Audit → RateLimit → Auth → RBAC), config pattern, and DI chain. All new code follows the project's established conventions: `domain/models.py` for ORM, `domain/schemas.py` for Pydantic, `api/v1/*.py` for routers, `adapters/` for infra.

## Architecture Decisions

| Decision | Choice | Tradeoffs considered | Rationale |
|----------|--------|---------------------|-----------|
| Auth foundation | Copy auth-login-platform | vs build from scratch | Proven JWT+RBAC+rate-limit+audit. Hex pattern already established. |
| Spatial DB | PostGIS + GeoAlchemy2 | vs raw GEOMETRY types | ST_DWithin index-friendly radius queries. GIST index on GEOGRAPHY(POINT, 4326). |
| Text search (MVP) | pg_trgm + GIN indexes | vs Elasticsearch | Zero infra cost. Adequate for <100K properties. ES migration path planned. |
| Matching computation | Real-time with Redis cache | vs batch cron jobs | Buyer-seller immediacy wins. Cache key `match:{buyer_id}`, TTL 1h. Debounce 60s. |
| File storage | S3-compatible (MinIO dev) | vs local filesystem | Scale-out via S3. MinIO for local dev parity. Django-style `storage` adapter. |

## Data Flow

```
Buyer updates preferences ──→ PUT /profiles ──→ invalidate Redis match:{buyer_id}
                                                      │
Seller publishes property ──→ POST /properties ──→ trigger async recompute ──→ Redis match:{*}
       │                                                    │
       ├── Upload photos ──→ MinIO ──→ PropertyPhoto.url    │
       │                                                    ▼
       └── Search ──→ pg_trgm + ST_DWithin ──→ results  Match engine (core/matching.py)
                     (GIN index + GIST index)          price×0.3 + location×0.25 + features×0.25 + area×0.2
```

## Domain Model (ERD Extension)

Extend auth `User` with one-to-one profiles. New standalone entities for real estate domain:

```
User (from auth) ──1:1── BuyerProfile (budget_range, locations JSONB, features JSONB)
User (from auth) ──1:1── SellerProfile (phone, company_name)
User (from auth) ──1:1── AgentProfile (license_number UNIQUE, agency_name)
User ──1:N── Property (type ENUM, operation ENUM, status ENUM, GEOGRAPHY, features JSONB)
Property ──1:N── PropertyPhoto (url, order, s3_key)
Property ──N:1── Project (nullable: name, construction_stage, total_units)
Property ──N:M── Favorite (user_id, property_id, UNIQUE constraint)
BuyerProfile ──N:M── Property → Match (score DECIMAL, score_breakdown JSONB, computed_at)
User ──1:N── Inquiry (from_user FK, to_user FK, property FK, message, status ENUM)
```

## API Contract

All endpoints at `/api/v1/`. Auth via JWT Bearer + RBAC guard from shared `deps.py`.

| Method | Endpoint | Role | Spec Ref |
|--------|----------|------|----------|
| POST | `/properties` | seller, agent | REQ-INMO-010 |
| GET | `/properties` | public (published only) | REQ-INMO-012 |
| GET | `/properties/{id}` | public | REQ-INMO-013 |
| PUT | `/properties/{id}` | owner | REQ-INMO-015 |
| DELETE | `/properties/{id}` | owner (soft) | REQ-INMO-015 |
| POST | `/properties/{id}/photos` | owner | REQ-INMO-014 |
| DELETE | `/properties/{id}/photos/{photo_id}` | owner | REQ-INMO-014 |
| GET | `/matches` | buyer | REQ-INMO-022 |
| POST | `/matches/compute` | buyer | REQ-INMO-024 |
| GET | `/matches/history` | buyer | REQ-INMO-023 |
| POST | `/inquiries` | buyer | REQ-INMO-030 |
| GET | `/inquiries` | any (sent/received) | REQ-INMO-033 |
| PUT | `/inquiries/{id}` | property owner | REQ-INMO-031 |
| GET | `/profiles/me` | any authenticated | REQ-INMO-004 |
| PUT | `/profiles/me` | any authenticated | REQ-INMO-004 |
| GET | `/favorites` | any authenticated | — |
| POST | `/favorites` | any authenticated | — |
| DELETE | `/favorites/{property_id}` | any authenticated | — |
| GET | `/admin/users` | admin | REQ-INMO-005 |
| GET | `/agent/dashboard/stats` | agent | REQ-INMO-044 |
| GET | `/agent/dashboard/listings` | agent | REQ-INMO-040 |
| GET | `/agent/dashboard/clients` | agent | REQ-INMO-041 |

## Matching Algorithm (core/matching.py)

```python
def compute_match(buyer: BuyerProfile, property: Property) -> dict:
    price_score   = score_price(buyer.budget_range, property.price) * 0.30
    loc_score     = score_location(buyer.locations, property.location) * 0.25
    feat_score    = score_features(buyer.features, property.features) * 0.25
    area_score    = score_area(buyer.area_range, property.area_m2) * 0.20
    total         = round(price_score + loc_score + feat_score + area_score, 2)
    return {"total": total, "breakdown": {...}}
```

Sub-scores normalized 0–100. Price uses linear decay outside budget. Location uses ST_DWithin radius + distance decay. Features uses Jaccard similarity on JSONB sets. Area uses linear decay outside range.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/domain/models.py` | Modify | Add BuyerProfile, SellerProfile, AgentProfile, Property, PropertyPhoto, Project, Match, Inquiry, Favorite |
| `app/domain/schemas.py` | Modify | Add Pydantic request/response schemas for all new entities |
| `app/core/matching.py` | Create | Weighted multi-factor scoring engine |
| `app/api/v1/properties.py` | Create | Property CRUD + search + photo management |
| `app/api/v1/matches.py` | Create | Match retrieval + recompute trigger |
| `app/api/v1/inquiries.py` | Create | Inquiry CRUD + status workflow |
| `app/api/v1/favorites.py` | Create | Favorite add/remove/list |
| `app/api/v1/profiles.py` | Create | Profile CRUD per role |
| `app/api/v1/admin.py` | Modify | Add admin user list endpoint |
| `app/api/v1/agent.py` | Create | Agent dashboard endpoints (V2) |
| `app/api/v1/router.py` | Modify | Include all new routers |
| `app/adapters/s3_storage.py` | Create | S3/MinIO file storage adapter |
| `app/config.py` | Modify | Add S3/MinIO settings, PostGIS DSN |
| `migrations/versions/002_inmobiliaria.py` | Create | PostGIS extension + all new tables + indexes |
| `tests/unit/test_matching.py` | Create | Scoring algorithm unit tests |
| `tests/integration/test_properties.py` | Create | Property CRUD + search integration |
| `tests/e2e/test_inmobiliaria_flow.py` | Create | End-to-end: register → publish → match → inquire |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `core/matching.py` scoring functions | Table-driven: price/location/feature/area edge cases |
| Integration | Property CRUD, search filters, inquiry flow | `pytest-asyncio` + `AsyncClient` + SQLite+PostGIS |
| E2E | Full buyer/seller/agent journey | httpx ASGI transport, fakeredis, test fixtures |

## Migration / Rollout

1. Copy auth-login-platform codebase (exclude `.git`, `.venv`, `__pycache__`)
2. Run `alembic upgrade head` (includes 002 migration: PostGIS ext + new tables)
3. Seed RBAC roles: buyer, seller, agent, admin
4. Deploy with feature flags: `ENABLE_MATCHING=true`, `ENABLE_AGENT_DASHBOARD=false` (V2)

Rollback: `alembic downgrade -1` removes new tables. Auth tables untouched. Redis `match:*` and `search:*` keys flushed.

## Open Questions

- [ ] Agent→buyer assignment flow: auto-assign or manual? (Spec REQ-INMO-041 assumes assignment exists but doesn't define it)
- [ ] Photo thumbnail generation: on-upload (blocking) or async? Leaning async to avoid upload latency
