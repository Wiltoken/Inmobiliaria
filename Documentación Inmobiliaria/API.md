# API Reference

## Overview

The Inmobiliaria Platform exposes a RESTful API via FastAPI. All endpoints are under `/api/v1/`.

**Base URL:** `https://inmobiliaria.example.com/api/v1/`

**Documentation:** `https://inmobiliaria.example.com/docs` (Swagger UI) or `/redoc` (ReDoc)

## Authentication

### JWT Flow

```
1. User submits credentials to POST /api/v1/auth/login
2. Server validates, returns:
   {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "token_type": "bearer",
     "expires_in": 900
   }
3. Client includes access_token in Authorization header:
   Authorization: Bearer eyJ...
4. When access_token expires, client calls POST /api/v1/auth/refresh
   with refresh_token to get new tokens
5. On logout, client calls POST /api/v1/auth/logout to blacklist tokens
```

### Token Types

| Token | Lifetime | Storage | Purpose |
|-------|----------|---------|---------|
| Access Token | 15 minutes | Memory only | API authorization |
| Refresh Token | 7 days | HTTPOnly cookie + Redis | Session continuity |

### Login

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "SecurePass123!"
}

Response 200:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}

Response 401:
{
  "detail": "Invalid credentials",
  "code": "INVALID_CREDENTIALS"
}

Response 423:
{
  "detail": "Account is locked. Try again in X minutes.",
  "code": "ACCOUNT_LOCKED",
  "locked_until": "2024-01-15T10:30:00Z"
}
```

### Refresh Token

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response 200:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <access_token>

Response 200:
{
  "message": "Successfully logged out"
}
```

### Register

```
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "newuser",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "role": "buyer",  // buyer | seller
  "consent_given": true
}

Response 201:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "newuser",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Properties

### Search Properties

```
GET /api/v1/properties/
Authorization: Bearer <token>
Query Parameters:
  - type: apartment | house | commercial | land | office | warehouse | room
  - operation: sale | rent | lease
  - status: active | pending | sold | rented
  - price_min: float
  - price_max: float
  - area_min: float (m²)
  - area_max: float (m²)
  - rooms_min: int
  - lat: float (search center latitude)
  - lon: float (search center longitude)
  - radius_km: float (default 10)
  - features: comma-separated list
  - q: string (full-text search in title/description)
  - page: int (default 1)
  - limit: int (default 20, max 100)
  - sort: price_asc | price_desc | created_at_desc | area_desc

Response 200:
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "apartment",
      "operation": "sale",
      "status": "active",
      "price": 250000000,
      "area_m2": 75.5,
      "rooms": 3,
      "bathrooms": 2,
      "location": {
        "type": "Point",
        "coordinates": [-74.0060, 40.7128]
      },
      "title": "Hermoso apartamento en Chapinero",
      "description": "...",
      "photos": [
        {"id": "...", "url": "https://...", "order": 0}
      ],
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "pages": 8
}
```

### Get Property

```
GET /api/v1/properties/{property_id}
Authorization: Bearer <token>

Response 200:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "apartment",
  "operation": "sale",
  "status": "active",
  "price": 250000000,
  "area_m2": 75.5,
  "rooms": 3,
  "bathrooms": 2,
  "location": {
    "type": "Point",
    "coordinates": [-74.0060, 40.7128]
  },
  "features": {
    "features": ["gym", "pool", "security"]
  },
  "title": "Hermoso apartamento en Chapinero",
  "description": "...",
  "is_active": true,
  "owner": {
    "id": "...",
    "username": "seller1"
  },
  "agent": {
    "id": "...",
    "username": "agent1",
    "agent_profile": {
      "license_number": "12345",
      "agency_name": "Inmobiliaria ABC"
    }
  },
  "photos": [...],
  "created_at": "2024-01-15T10:30:00Z",
  "published_at": "2024-01-15T12:00:00Z"
}
```

### Create Property

```
POST /api/v1/properties/
Authorization: Bearer <token> (seller or agent role)
Content-Type: application/json

{
  "type": "apartment",
  "operation": "sale",
  "price": 250000000,
  "area_m2": 75.5,
  "rooms": 3,
  "bathrooms": 2,
  "location": {
    "type": "Point",
    "coordinates": [-74.0060, 40.7128]
  },
  "title": "Hermoso apartamento en Chapinero",
  "description": "Excelente ubicación...",
  "features": {
    "features": ["gym", "pool", "security"]
  }
}

Response 201:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  ...
}
```

### Update Property

```
PATCH /api/v1/properties/{property_id}
Authorization: Bearer <token> (owner or agent)
Content-Type: application/json

{
  "price": 240000000,
  "description": "Updated description..."
}

Response 200:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  ...
}
```

### Upload Property Photos

```
POST /api/v1/properties/{property_id}/photos
Authorization: Bearer <token>
Content-Type: multipart/form-data

files: [photo1.jpg, photo2.jpg]

Response 201:
{
  "uploaded": [
    {"id": "...", "url": "https://minio...", "order": 0},
    {"id": "...", "url": "https://minio...", "order": 1}
  ]
}
```

### Delete Property

```
DELETE /api/v1/properties/{property_id}
Authorization: Bearer <token> (owner or admin)

Response 204: No Content
```

## Matches

### Get My Matches (Buyer)

```
GET /api/v1/matches/
Authorization: Bearer <token> (buyer role)
Query Parameters:
  - page: int (default 1)
  - limit: int (default 20)

Response 200:
{
  "items": [
    {
      "id": "...",
      "property_id": "...",
      "score": 87.5,
      "score_breakdown": {
        "price": 100.0,
        "location": 85.0,
        "features": 75.0,
        "area": 90.0
      },
      "computed_at": "2024-01-15T10:30:00Z",
      "property": {
        "id": "...",
        "title": "...",
        "price": 250000000,
        ...
      }
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 20,
  "pages": 3
}
```

### Trigger Match Recomputation

```
POST /api/v1/matches/recompute
Authorization: Bearer <token> (buyer role)

Response 202:
{
  "message": "Match recomputation started",
  "task_id": "..."
}
```

## Inquiries

### Create Inquiry

```
POST /api/v1/inquiries/
Authorization: Bearer <token>
Content-Type: application/json

{
  "property_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Me interesa esta propiedad. ¿Podemos agendar una visita?",
  "contact_preference": "whatsapp"
}

Response 201:
{
  "id": "...",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get My Inquiries (as Buyer)

```
GET /api/v1/inquiries/
Authorization: Bearer <token>
Query Parameters:
  - status: pending | replied | interested | not_interested
  - page: int
  - limit: int

Response 200:
{
  "items": [...],
  "total": 10,
  ...
}
```

### Get Inquiries for My Properties (as Seller/Agent)

```
GET /api/v1/inquiries/received
Authorization: Bearer <token> (seller or agent role)

Response 200:
{
  "items": [
    {
      "id": "...",
      "from_user": {"id": "...", "username": "buyer1"},
      "property": {"id": "...", "title": "..."},
      "message": "...",
      "status": "pending",
      "created_at": "..."
    }
  ],
  ...
}
```

### Respond to Inquiry

```
PATCH /api/v1/inquiries/{inquiry_id}
Authorization: Bearer <token> (seller or agent)
Content-Type: application/json

{
  "status": "replied",
  "response_message": "Podemos agendar una visita mañana a las 3pm.",
  "response_action": "scheduled_viewing"
}

Response 200:
{
  "id": "...",
  "status": "replied",
  ...
}
```

## Profiles

### Get My Profile

```
GET /api/v1/profiles/me
Authorization: Bearer <token>

Response 200:
{
  "id": "...",
  "email": "user@example.com",
  "username": "user1",
  "roles": ["buyer"],
  "buyer_profile": {
    "budget_min": 200000000,
    "budget_max": 400000000,
    "preferred_locations": [
      {"lat": 4.7110, "lon": -74.0721, "radius_km": 5}
    ],
    "preferred_property_types": ["apartment", "house"],
    ...
  },
  ...
}
```

### Update Buyer Profile

```
PATCH /api/v1/profiles/me/buyer
Authorization: Bearer <token> (buyer role)
Content-Type: application/json

{
  "budget_min": 200000000,
  "budget_max": 400000000,
  "preferred_locations": [
    {"lat": 4.7110, "lon": -74.0721, "radius_km": 5},
    {"lat": 4.6247, "lon": -74.0636, "radius_km": 10}
  ],
  "rooms_min": 2,
  "bathrooms_min": 1,
  "area_min": 50,
  "preferred_property_types": ["apartment", "house"],
  "preferred_features": {
    "features": ["gym", "security", "parking"]
  }
}

Response 200:
{
  "id": "...",
  "budget_min": 200000000,
  ...
}
```

### Update Seller Profile

```
PATCH /api/v1/profiles/me/seller
Authorization: Bearer <token> (seller role)

{
  "phone": "+573001234567",
  "company_name": "Mi Inmobiliaria SAS"
}

Response 200:
{
  "id": "...",
  "phone": "+573001234567",
  ...
}
```

## Favorites

### Add to Favorites

```
POST /api/v1/favorites/{property_id}
Authorization: Bearer <token>

Response 201:
{
  "id": "...",
  "property_id": "...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Remove from Favorites

```
DELETE /api/v1/favorites/{property_id}
Authorization: Bearer <token>

Response 204: No Content
```

### List My Favorites

```
GET /api/v1/favorites/
Authorization: Bearer <token>
Query Parameters:
  - page: int
  - limit: int

Response 200:
{
  "items": [
    {
      "id": "...",
      "property": {...},
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  ...
}
```

## Admin Endpoints

### List Users

```
GET /api/v1/admin/users
Authorization: Bearer <token> (admin role)
Query Parameters:
  - role: buyer | seller | agent
  - is_active: true | false
  - page: int
  - limit: int

Response 200:
{
  "items": [...],
  "total": 150,
  ...
}
```

### Approve Property

```
POST /api/v1/admin/properties/{property_id}/approve
Authorization: Bearer <token> (admin role)

Response 200:
{
  "id": "...",
  "status": "active",
  "published_at": "2024-01-15T10:30:00Z"
}
```

### Reject Property

```
POST /api/v1/admin/properties/{property_id}/reject
Authorization: Bearer <token> (admin role)
Content-Type: application/json

{
  "reason": "Photos do not match the property description"
}

Response 200:
{
  "id": "...",
  "status": "rejected",
  "rejection_reason": "Photos do not match..."
}
```

### Lock/Unlock User

```
POST /api/v1/admin/users/{user_id}/lock
Authorization: Bearer <token> (admin role)

Response 200:
{
  "id": "...",
  "is_locked": true,
  "locked_until": null
}

POST /api/v1/admin/users/{user_id}/unlock
Authorization: Bearer <token> (admin role)

Response 200:
{
  "id": "...",
  "is_locked": false,
  "locked_until": null
}
```

## Agent Endpoints

### Agent Dashboard

```
GET /api/v1/agent/dashboard
Authorization: Bearer <token> (agent role)

Response 200:
{
  "total_properties": 25,
  "active_properties": 18,
  "total_inquiries": 42,
  "pending_inquiries": 5,
  "recent_inquiries": [...],
  "clients": [
    {
      "id": "...",
      "username": "buyer1",
      "inquiry_count": 3
    }
  ]
}
```

### My Clients

```
GET /api/v1/agent/clients
Authorization: Bearer <token> (agent role)

Response 200:
{
  "items": [
    {
      "id": "...",
      "username": "buyer1",
      "email": "buyer@example.com",
      "buyer_profile": {...},
      "inquiry_count": 5
    }
  ],
  ...
}
```

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Human-readable error message",
  "code": "ERROR_CODE",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

### Common Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | VALIDATION_ERROR | Request validation failed |
| 401 | UNAUTHORIZED | Missing or invalid token |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource already exists |
| 422 | UNPROCESSABLE_ENTITY | Business logic error |
| 423 | LOCKED | Account or resource locked |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |
