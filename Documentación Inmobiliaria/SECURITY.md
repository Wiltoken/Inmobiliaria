# Security

## Authentication

### JWT Implementation

The platform uses JWT (JSON Web Tokens) with a dual-token system:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JWT Authentication Flow                             │
└─────────────────────────────────────────────────────────────────────────────┘

1. LOGIN
   ┌────────┐                          ┌────────┐
   │ Client │                          │  API   │
   └───┬────┘                          └───┬────┘
       │                                    │
       │  POST /api/v1/auth/login           │
       │  {username, password}              │
       │ ──────────────────────────────────▶│
       │                                    │
       │                         ┌───────────▼───────────┐
       │                         │ 1. Validate password  │
       │                         │ 2. Check lockout      │
       │                         │ 3. Generate tokens    │
       │                         └───────────┬───────────┘
       │                                    │
       │  {access_token, refresh_token}     │
       │ ◀──────────────────────────────────│
       │                                    │
       │ 2. Store tokens securely           │
       │   (HTTPOnly cookie for refresh)    │

2. API REQUESTS
   ┌────────┐                          ┌────────┐
   │ Client │                          │  API   │
   └───┬────┘                          └───┬────┘
       │                                    │
       │  GET /api/v1/properties/           │
       │  Authorization: Bearer <access>    │
       │ ──────────────────────────────────▶│
       │                                    │
       │                         ┌───────────▼───────────┐
       │                         │ 1. Validate JWT      │
       │                         │ 2. Check blacklist    │
       │                         │ 3. Check RBAC         │
       │                         └───────────┬───────────┘
       │                                    │
       │  200 OK + data                     │
       │ ◀──────────────────────────────────│

3. TOKEN REFRESH (when access_token expires)
   ┌────────┐                          ┌────────┐
   │ Client │                          │  API   │
   └───┬────┘                          └───┬────┘
       │                                    │
       │  POST /api/v1/auth/refresh         │
       │  {refresh_token}                   │
       │ ──────────────────────────────────▶│
       │                                    │
       │                         ┌───────────▼───────────┐
       │                         │ 1. Validate refresh  │
       │                         │ 2. Rotate tokens     │
       │                         │ 3. Blacklist old     │
       │                         └───────────┬───────────┘
       │                                    │
       │  {new_access, new_refresh}         │
       │ ◀──────────────────────────────────│

4. LOGOUT
   ┌────────┐                          ┌────────┐
   │ Client │                          │  API   │
   └───┬────┘                          └───┬────┘
       │                                    │
       │  POST /api/v1/auth/logout          │
       │  Authorization: Bearer <access>    │
       │ ──────────────────────────────────▶│
       │                                    │
       │                         ┌───────────▼───────────┐
       │                         │ 1. Blacklist access   │
       │                         │ 2. Remove refresh     │
       │                         │ 3. Audit log          │
       │                         └───────────┬───────────┘
       │                                    │
       │  200 OK                            │
       │ ◀──────────────────────────────────│
```

### Token Storage

| Token | Storage | Rationale |
|-------|---------|-----------|
| Access Token | Memory only | Short-lived (15 min), shouldn't persist |
| Refresh Token | HTTPOnly cookie + Redis | Long-lived (7 days), needs server-side revocation |

### Token Payload

```json
// Access Token
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "roles": ["buyer", "agent"],
  "tenant_id": "tenant-uuid",
  "jti": "unique-token-id",
  "type": "access",
  "iat": 1705312200,
  "exp": 1705313100
}

// Refresh Token
{
  "sub": "user-uuid",
  "jti": "unique-token-id",
  "type": "refresh",
  "iat": 1705312200,
  "exp": 1705917000
}
```

## Authorization

### RBAC Matrix

| Endpoint | Admin | Agent | Seller | Buyer | Anonymous |
|----------|-------|-------|--------|-------|-----------|
| **Auth** | | | | | |
| POST /auth/login | ✓ | ✓ | ✓ | ✓ | ✓ |
| POST /auth/register | ✓ | ✓ | ✓ | ✓ | ✓ |
| POST /auth/refresh | ✓ | ✓ | ✓ | ✓ | ✓ |
| POST /auth/logout | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Properties** | | | | | |
| GET /properties/ | ✓ | ✓ | ✓ | ✓ | ✓ |
| GET /properties/{id} | ✓ | ✓ | ✓ | ✓ | ✓ |
| POST /properties/ | ✓ | ✓ | ✓ | ✗ | ✗ |
| PATCH /properties/{id} | ✓ | ✓ | ✓* | ✗ | ✗ |
| DELETE /properties/{id} | ✓ | ✓ | ✓* | ✗ | ✗ |
| POST /properties/{id}/photos | ✓ | ✓ | ✓* | ✗ | ✗ |
| **Matches** | | | | | |
| GET /matches/ | ✓ | ✓ | ✓ | ✓ | ✗ |
| POST /matches/recompute | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Inquiries** | | | | | |
| POST /inquiries/ | ✓ | ✓ | ✓ | ✓ | ✗ |
| GET /inquiries/ | ✓ | ✓ | ✓ | ✓ | ✗ |
| GET /inquiries/received | ✓ | ✓ | ✓ | ✗ | ✗ |
| PATCH /inquiries/{id} | ✓ | ✓ | ✓ | ✗ | ✗ |
| **Profiles** | | | | | |
| GET /profiles/me | ✓ | ✓ | ✓ | ✓ | ✗ |
| PATCH /profiles/me/buyer | ✓ | ✓ | ✗ | ✓ | ✗ |
| PATCH /profiles/me/seller | ✓ | ✓ | ✓ | ✗ | ✗ |
| **Favorites** | | | | | |
| GET /favorites/ | ✓ | ✓ | ✓ | ✓ | ✗ |
| POST /favorites/{id} | ✓ | ✓ | ✓ | ✓ | ✗ |
| DELETE /favorites/{id} | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Admin** | | | | | |
| GET /admin/users | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST /admin/properties/{id}/approve | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST /admin/properties/{id}/reject | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST /admin/users/{id}/lock | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Agent** | | | | | |
| GET /agent/dashboard | ✓ | ✓ | ✗ | ✗ | ✗ |
| GET /agent/clients | ✓ | ✓ | ✗ | ✗ | ✗ |

*Owner of the property or admin

## Rate Limiting

### Layer 1: Nginx (30 req/s per IP)

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

location /api/ {
    limit_req zone=api burst=50 nodelay;
}
```

### Layer 2: Redis Token Bucket (5 req/s per IP for auth, configurable)

```python
async def rate_limit_check(
    ip_address: str,
    max_requests: int = 5,
    window_seconds: int = 1,
) -> tuple[bool, int]:
    """Token-bucket rate limiting using Redis sorted sets."""
    key = f"rate_limit:{ip_address}"
    now_ts = await client.time()
    now_ms = int(now_ts * 1000)
    window_start = now_ms - (window_seconds * 1000)

    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {f"{now_ms}": now_ts})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 1)
    results = await pipe.execute()

    count = results[2]
    allowed = count <= max_requests
    remaining = max(0, max_requests - count)
    return allowed, remaining
```

### Stricter Limits for Auth Endpoints

| Endpoint | Limit | Burst |
|----------|-------|-------|
| `/api/v1/auth/login` | 5/min | 10 |
| `/api/v1/auth/register` | 3/min | 5 |
| `/api/v1/auth/refresh` | 10/min | 15 |
| Other API endpoints | 30/s | 50 |

## Data Protection

### Password Hashing

- Algorithm: bcrypt with auto-detection
- Default rounds: 12 (configurable via environment)
- No password stored in plain text

```python
from app.core.security import hash_password, verify_password

# Hash password
password_hash = hash_password("SecurePass123!")

# Verify password
is_valid = verify_password("SecurePass123!", password_hash)
```

### TLS Configuration

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
```

### Secrets Management

Environment variables for all secrets:
- `SECRET_KEY` - JWT signing key
- `POSTGRES_PASSWORD` - Database password
- `S3_SECRET_KEY` - MinIO/S3 secret
- `SMTP_PASSWORD` - Email password

Never commit `.env` to version control.

## Audit Trail

### Logged Events

| Event | User | IP | Details |
|-------|------|-----|---------|
| LOGIN_SUCCESS | ✓ | ✓ | User agent |
| LOGIN_FAILED | ✓ | ✓ | Attempt count |
| LOGOUT | ✓ | ✓ | - |
| TOKEN_REFRESH | ✓ | ✓ | - |
| PASSWORD_CHANGE | ✓ | ✓ | - |
| ACCOUNT_LOCKED | ✓ | ✓ | Lockout duration |
| ACCOUNT_UNLOCKED | ✓ | ✓ | Admin who unlocked |
| PROPERTY_CREATED | ✓ | ✓ | Property ID |
| PROPERTY_APPROVED | ✓ | ✓ | Property ID |
| PROPERTY_REJECTED | ✓ | ✓ | Property ID, reason |

### Audit Log Schema

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    details: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

## OWASP Mitigations

| OWASP Top 10 | Mitigation |
|--------------|------------|
| A01 Broken Access Control | RBAC middleware, ownership checks |
| A02 Cryptographic Failures | bcrypt, TLS 1.2+, JWT |
| A03 Injection | SQLAlchemy ORM, parameterized queries |
| A04 Insecure Design | Rate limiting, lockout, input validation |
| A05 Security Misconfiguration | Secure defaults, CORS, headers |
| A06 Vulnerable Components | Dependency scanning, pinned versions |
| A07 Auth Failures | JWT rotation, lockout, audit logs |
| A08 Data Integrity Failures | HTTPS, signed tokens |
| A09 Logging Failures | Structured logging, audit trail |
| A10 SSRF | URL validation, whitelist S3 endpoints |

### Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self' ..." always;
add_header Strict-Transport-Security "max-age=31536000" always;
```

## Colombian Law Compliance (Ley 1581 de 2012)

### Data Classification

| Data Type | Classification | Retention |
|-----------|----------------|-----------|
| User PII (email, name) | Sensitive | Account lifetime + 30 days |
| Password hashes | Critical | Never deleted (required) |
| Audit logs | Regulated | 365 days minimum |
| Property photos | Personal | Until property deleted |
| Location data | Sensitive | Anonymized after 1 year |

### Rights Implementation

| Right | Implementation |
|-------|----------------|
| Access | GET /admin/users/{id} for admins, self via /profiles/me |
| Correction | PATCH /profiles/me/* endpoints |
| Deletion | DELETE /profiles/me (soft delete) |
| Revocation of consent | Setting consent_given_at = NULL |

### Required Disclosures

```python
# Consent request during registration
{
    "consent_text": "Autorizo el tratamiento de mis datos personales...",
    "consent_required": true,
    "policy_url": "https://inmobiliaria.example.com/privacy"
}
```

### Audit Log Retention

```python
# Cleanup task runs daily, keeps 365 days minimum
async def cleanup_old_audit_logs():
    cutoff = datetime.utcnow() - timedelta(days=settings.audit_retention_days)
    await session.execute(
        delete(AuditLog).where(AuditLog.created_at < cutoff)
    )
```

## Account Lockout

### Lockout Flow

```
Failed Login Attempt
        │
        ▼
┌───────────────────┐
│ Check attempts    │
│ from Redis        │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     ┌───────────────────┐
│ attempts < max    │ ──▶ │ Return 401        │
└───────────────────┘     └───────────────────┘
          │
          ▼ No (≥ max)
┌───────────────────┐
│ Set lockout in    │
│ Redis (TTL=15min) │
│ Set is_locked     │
│ in DB             │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Return 423        │
│ LOCKED            │
└───────────────────┘
```

### Configuration

```python
class AuthSettings(BaseSettings):
    max_login_attempts: int = Field(default=3)
    lockout_duration_minutes: int = Field(default=15)
```
