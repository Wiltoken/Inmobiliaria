# Development Guide

## Project Structure

```
inmobiliaria/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Pydantic settings (all config)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py         # API v1 router (aggregates all endpoints)
│   │       ├── deps.py           # Dependency injection (auth, db session, etc.)
│   │       ├── auth.py           # Authentication endpoints
│   │       ├── properties.py     # Property CRUD endpoints
│   │       ├── matches.py        # Match computation endpoints
│   │       ├── inquiries.py      # Inquiry endpoints
│   │       ├── profiles.py        # User profile endpoints
│   │       ├── favorites.py      # Favorites endpoints
│   │       ├── admin.py          # Admin-only endpoints
│   │       └── agent.py          # Agent-only endpoints
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py           # Password hashing, JWT encoding/decoding
│   │   ├── matching.py           # Match scoring algorithm
│   │   ├── celery_app.py         # Celery app + periodic tasks
│   │   ├── exceptions.py         # Custom exceptions
│   │   └── middleware.py         # Auth, RBAC, RateLimit, AuditLog middleware
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy ORM models (all entities)
│   │   └── schemas.py            # Pydantic DTOs (request/response models)
│   │
│   ├── ports/
│   │   ├── __init__.py
│   │   └── captcha.py            # Captcha port interface
│   │
│   └── adapters/
│       ├── __init__.py
│       ├── database.py           # SQLAlchemy async engine, session
│       ├── redis_client.py       # Async Redis client + operations
│       ├── s3_storage.py         # MinIO/S3 storage adapter
│       └── google_recaptcha.py   # reCAPTCHA v3 adapter
│
├── migrations/
│   ├── env.py                    # Alembic migration environment
│   └── versions/                  # Alembic migration scripts
│       ├── 001_initial.py
│       └── 002_inmobiliaria.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/                     # Unit tests (no I/O)
│   │   ├── test_config.py
│   │   ├── test_security.py
│   │   ├── test_matching.py
│   │   └── test_schemas.py
│   ├── integration/              # Integration tests (DB, Redis)
│   │   ├── test_auth_service.py
│   │   ├── test_properties.py
│   │   └── test_rate_limiter.py
│   └── e2e/                      # End-to-end tests (full stack)
│       ├── test_auth_flow.py
│       └── test_lockout.py
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md
│   ├── INFRASTRUCTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   ├── SECURITY.md
│   ├── DEVELOPMENT.md
│   └── OPERATIONS.md
│
├── scripts/                      # Operational scripts
│   ├── backup.sh
│   └── restore.sh
│
├── nginx/                        # Nginx configuration
│   ├── nginx.conf
│   └── conf.d/
│       └── inmobiliaria.conf
│
├── pgbouncer/                    # PgBouncer configuration
│   ├── pgbouncer.ini
│   └── userlist.txt
│
├── docker-compose.yml            # Base compose (postgres + redis + api)
├── docker-compose.dev.yml       # Development compose (hot reload)
├── docker-compose.prod.yml      # Production compose (full stack)
├── Dockerfile                    # API image
├── Makefile                      # Operational commands
├── alembic.ini                   # Alembic configuration
├── pyproject.toml                # Project metadata + dependencies
└── README.md
```

## Local Development Setup

### Option 1: Docker Compose (Recommended)

```bash
# 1. Start development environment
make dev

# Or directly
docker compose -f docker-compose.dev.yml up -d

# 2. Run migrations
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# 3. View logs
docker compose -f docker-compose.dev.yml logs -f api

# 4. Access API
open http://localhost:8000/docs
```

### Option 2: Local Python (for testing only)

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Start required services
docker compose -f docker-compose.yml up -d postgres redis

# 4. Run migrations
alembic upgrade head

# 5. Start API with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

### All Tests

```bash
make test

# Or
python -m pytest tests/ -v --tb=short
```

### Unit Tests Only

```bash
make test-unit

# Or
python -m pytest tests/unit/ -v --tb=short
```

### Integration Tests

```bash
make test-integration

# Or
python -m pytest tests/integration/ -v --tb=short
```

### E2E Tests

```bash
make test-e2e

# Or
python -m pytest tests/e2e/ -v --tb=short
```

### With Coverage

```bash
make test-cov

# Or
python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term
```

## Code Style

### Ruff (Linting + Formatting)

```bash
# Check for issues
make lint-check

# Auto-fix issues
make lint

# Format code
make format
```

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
```

### Type Checking (MyPy)

```bash
mypy app/ --ignore-missing-imports
```

## Adding New Features

### Port/Adapter Pattern

When adding external integrations, follow the port/adapter pattern:

```
1. Define port interface in app/ports/
2. Implement adapter in app/adapters/
3. Inject via dependency in app/api/v1/deps.py
```

### Example: Adding Email Notifications

```python
# 1. Define port interface
# app/ports/email.py
from abc import ABC, abstractmethod

class EmailPort(ABC):
    @abstractmethod
    async def send_password_reset(self, to: str, token: str) -> None: ...

    @abstractmethod
    async def send_inquiry_notification(self, to: str, inquiry: dict) -> None: ...

# 2. Implement adapter
# app/adapters/smtp_email.py
from app.ports.email import EmailPort

class SMTPEmailAdapter(EmailPort):
    async def send_password_reset(self, to: str, token: str) -> None:
        # SMTP implementation
        ...

# 3. Register in deps.py
# app/api/v1/deps.py
from app.adapters.smtp_email import SMTPEmailAdapter

async def get_email_port() -> EmailPort:
    return SMTPEmailAdapter()

# 4. Use in endpoint
@router.post("/reset-password")
async def reset_password(
    email: str,
    email_port: EmailPort = Depends(get_email_port)
):
    await email_port.send_password_reset(email, token)
```

### Adding New ORM Models

```python
# 1. Add model in app/domain/models.py
class MyEntity(Base):
    __tablename__ = "my_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

# 2. Create migration
alembic revision --autogenerate -m "Add my_entity table"

# 3. Add Pydantic schema in app/domain/schemas.py
class MyEntityCreate(BaseModel):
    name: str

class MyEntityResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# 4. Add endpoints in app/api/v1/my_entities.py
@router.post("/", response_model=MyEntityResponse)
async def create_entity(
    data: MyEntityCreate,
    session: AsyncSession = Depends(get_db),
):
    entity = MyEntity(name=data.name)
    session.add(entity)
    await session.commit()
    await session.refresh(entity)
    return entity
```

## Database Migrations

### Create Migration

```bash
# After modifying models
docker compose -f docker-compose.dev.yml exec api alembic revision --autogenerate -m "Description"
```

### Run Migrations

```bash
# Apply all
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# Rollback one
docker compose -f docker-compose.dev.yml exec api alembic downgrade -1
```

### Migration Best Practices

1. Always use `--autogenerate` for schema changes
2. Review generated migration before applying
3. Never modify existing migrations (create new one)
4. Test rollback locally before production

## Debugging

### Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or with ipdb
import ipdb; ipdb.set_trace()
```

### FastAPI Debug Mode

```bash
# In docker-compose.dev.yml, API service:
uvicorn app.main:app --reload --log-level debug
```

### SQLAlchemy SQL Logging

```python
# In .env
LOG_LEVEL=DEBUG

# Or in config
engine = create_async_engine(url, echo=True)
```

### Redis Inspection

```bash
# Connect to Redis
docker compose -f docker-compose.dev.yml exec redis redis-cli

# List keys
KEYS *

# Get rate limit
GET rate_limit:192.168.1.1

# Delete key
DEL rate_limit:192.168.1.1
```

## Hot Reload

### Development Mode

The API container has volume mount for hot reload:

```yaml
# docker-compose.dev.yml
api:
  volumes:
    - .:/app
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Making Changes

1. Edit files in `app/` directory
2. Changes auto-reload (no container restart needed)
3. Database schema changes still require migration

## Dependency Management

### Adding a New Dependency

```bash
# Install and update pyproject.toml
pip install new-package
pip install new-package --save-extras dev

# Or edit pyproject.toml directly
[project]
dependencies = [
    ...,
    "new-package>=1.0.0",
]
```

### Lock File (for reproducibility)

```bash
pip install pip-tools
pip-compile pyproject.toml
```
