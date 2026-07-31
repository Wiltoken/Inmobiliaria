# Proposal: Inmobiliaria Real Estate Matching Platform

## Intent

Build an intelligent property-buyer matching platform for the Colombian real estate market. Generic listing sites (Fincaraíz, Metrocuadrado) offer catalogs but no personalized matching. This platform combines buyer profiling, weighted multi-factor scoring, and agent management in a single system — solving the disconnect between what buyers want and what agents list.

## Scope

### In Scope
- Role-based user registration (buyer, seller, agent, admin) reusing auth-login-platform JWT + RBAC
- Property CRUD with photos, features, geospatial location (PostGIS)
- Buyer preference profiling (budget, location, rooms, features)
- Full-text + geospatial search with filters (type, price, radius, rooms, features)
- Weighted matching engine: price (30%), location (25%), features (25%), area (20%)
- Buyer → Seller/Agent inquiries per property
- Agent dashboard for managing listings and client matches (V2)

### Out of Scope
- Real-time chat/messaging
- Mobile apps (API-first, add later)
- Payment/transaction processing
- ML-based recommendations (starts rule-based)
- VR/360 tours
- Contract/document management

## Personas

| Persona | Role | Primary Workflow |
|---------|------|------------------|
| Comprador | Buyer | Register → set preferences → browse matches → inquire |
| Vendedor | Seller | Register → publish property with photos → manage inquiries |
| Agente | Agent | Register → manage multiple listings → view client matches |
| Admin | Admin | Moderate listings, manage users, platform oversight |

## Capabilities

> This section is the CONTRACT between proposal and specs phases.
> The sdd-spec agent reads this to know exactly which spec files to create or update.

### New Capabilities
- `user-profiles`: Registration + role-based profiles (buyer, seller, agent) extending auth User model
- `property-management`: Property CRUD, search, filter, photo upload, geospatial queries
- `buyer-matching`: Preference profile storage, weighted scoring algorithm, explainable score breakdown
- `inquiries-contact`: Buyer-to-seller/agent inquiry creation and status tracking
- `agent-dashboard`: Agent manages multiple listings and views client match data (V2)

### Modified Capabilities
- None — greenfield project, no existing specs to modify

## Approach

Copy `auth-login-platform` (FastAPI async, SQLAlchemy 2.0, PostgreSQL 16, Redis 7, hexagonal architecture) as foundation. Extend with new domain modules:

1. **Properties**: ORM models (Property, PropertyPhoto, Project) with GeoAlchemy2 spatial types
2. **Profiles**: BuyerProfile, SellerProfile, AgentProfile linked to base User
3. **Matching**: `core/matching.py` scoring engine with Redis caching
4. **Search**: pg_trgm + GIN indexes for text, PostGIS ST_DWithin for geo
5. **Inquiries**: Simple contact flow with status tracking

API versioned at `/api/v1/`. Hexagonal ports/adapters pattern maintained.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/domain/models/` | New | Property, Project, Match, Inquiry, Favorite, Profile models |
| `src/api/routers/` | New | properties, profiles, matches, inquiries, favorites routers |
| `src/core/matching.py` | New | Weighted multi-factor scoring engine |
| `alembic/versions/` | New | Migration for all new tables + PostGIS extension |
| `src/infrastructure/` | New | GeoAlchemy2 config, pg_trgm indexes, S3 photo storage |
| `auth-login-platform/*` | Copied | Base hexagonal structure, JWT, RBAC, middleware, deps |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| GeoAlchemy2 async compatibility | Medium | Fallback to raw SQL for ST_DWithin queries |
| Match computation O(N×M) at scale | High | Pre-filter with ST_DWithin + price range, cache in Redis |
| Search degradation at 100K+ properties | Medium | Plan Elasticsearch migration path, monitor query times |
| Spanish full-text search quality | Low | Verify PG16 Spanish dictionary, test pg_trgm fallback |

## Rollback Plan

1. Revert the last git commit(s) for new modules (properties, profiles, matching)
2. Run `alembic downgrade -1` to remove new tables (PostGIS extension stays)
3. Flush Redis cache keys prefixed with `match:` and `search:`
4. No data loss: base auth platform remains untouched, only new tables dropped

## Dependencies

- `auth-login-platform` repository (foundation to copy)
- PostgreSQL 16 with PostGIS 3.5 extension installed
- Redis 7 for caching and rate limiting
- S3-compatible storage for property photos (MinIO for dev)

## Success Criteria

- [ ] Buyer can register, set preferences, and receive matched properties with explainable scores
- [ ] Seller can publish a property with photos, features, and geospatial location
- [ ] Agent can manage multiple listings and view which buyers match their properties
- [ ] Search returns relevant results in <500ms for up to 10K properties
- [ ] Match scores include score_breakdown JSONB showing per-factor contribution
- [ ] All API endpoints follow hexagonal ports/adapters pattern consistently
