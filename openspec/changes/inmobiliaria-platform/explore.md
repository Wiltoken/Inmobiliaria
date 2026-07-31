# Exploration: Inmobiliaria — Real Estate Matching Platform

## Current State

Greenfield project. The foundation is `auth-login-platform` — a hexagonal JWT auth platform (FastAPI async, SQLAlchemy 2.0, PostgreSQL 16, Redis 7) with RBAC, rate limiting, audit logging, and Colombian Ley 1581 compliance.

## Domain Model

### Users & Profiles (extends auth User, RBAC roles: buyer, seller, agent, admin)

```
User (from auth)
  ├── BuyerProfile: budget_min, budget_max, preferred_locations (JSONB),
  │     desired_rooms, desired_bathrooms, desired_area_min, desired_area_max,
  │     preferred_features[], preferred_property_types[]
  ├── SellerProfile: phone, company_name (nullable), properties[]
  └── AgentProfile: license_number, agency_name, managed_listings[], clients[]
```

### Property (Inmueble)

- **type**: ENUM(house, apartment, office, land, commercial, warehouse)
- **operation**: ENUM(sale, rent)
- **status**: ENUM(draft, published, reserved, sold, archived)
- **location**: GEOGRAPHY(POINT, 4326) via GeoAlchemy2
- **features**: JSONB (amenities list)
- **photos**: via PropertyPhoto table (S3 URLs)
- **price**: DECIMAL, currency (default COP)
- **area_m2**, rooms, bathrooms, parking_spots, floors, stratum, year_built, construction_type

### Other Entities

- **Project**: development grouping, construction_stage ENUM, total_units/available_units
- **Match**: buyer_id FK→BuyerProfile, property_id FK→Property, score (0-100), score_breakdown JSONB
- **Inquiry**: from_user FK→User, to_user FK→User, property FK→Property, status ENUM
- **Favorite**: user_id FK→User, property_id FK→Property, unique(user, property)

## Matching Algorithm

Weighted Multi-Factor Scoring (0–100):
```
Score = (price × 0.30) + (location × 0.25) + (features × 0.25) + (area × 0.20)
```

1. **Price (30%)**: Normalized budget-vs-price proximity, linear decay outside range
2. **Location (25%)**: ST_DWithin radius query with geography type, distance decay
3. **Features (25%)**: Jaccard similarity on JSONB feature sets
4. **Area (20%)**: Area_m2 vs desired range, linear decay

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| FastAPI >=0.115 | API framework |
| SQLAlchemy 2.0 async | ORM |
| PostgreSQL 16 + PostGIS 3.5 | DB + spatial |
| GeoAlchemy2 + Shapely | Spatial types |
| Redis 7 | Caching, rate limit |
| pg_trgm + GIN indexes | Text search |

## Architecture

Hexagonal (same as auth-login-platform). Copy auth foundation, extend with:
- New ORM models (Property, Project, Match, Inquiry, Favorite, Profiles)
- New API routers (properties, projects, matches, inquiries, favorites)
- `core/matching.py` scoring engine
- GeoAlchemy2 spatial types
- Keep middleware, security, deps, config as-is

API versioned at `/api/v1/`.

## MVP Scope (Priority 1)

1. User registration with buyer/seller profiles (RBAC)
2. Property CRUD (sellers/agents only)
3. Property search/filter: type, operation, price_range, city, rooms, bathrooms, area_range + pg_trgm text
4. Buyer preference profile
5. Basic match scoring (on-demand)
6. Auth (login, refresh, logout, RBAC)

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth foundation | Copy auth-login-platform | Proven hexagonal pattern, RBAC, rate-limit, audit |
| Spatial DB | PostGIS + GeoAlchemy2 | ST_DWithin index-friendly, battle-tested |
| Text search | pg_trgm + tsvector | No external dependency, adequate for MVP |
| Matching | Weighted multi-factor (no ML) | Transparent, debuggable, no training data |
| Feature storage | JSONB on Property | Flexible schema, avoids EAV |
| Filter params | Pydantic BaseModel query dep | FastAPI conventions |

## Risks

- **GeoAlchemy2 async compatibility**: Fallback to raw SQL for ST_DWithin
- **Search at scale (100K+ properties)**: Plan Elasticsearch migration path
- **Match computation O(N×M)**: Pre-filter with ST_DWithin + price range, cache in Redis
- **Spanish full-text search**: Verify PG16 Spanish dictionary availability

## Next Steps

1. `sdd-propose` — formalize scope, personas, workflows
2. `sdd-spec` — delta specs with Given/When/Then
3. `sdd-design` — detailed design with ERD and API contracts
