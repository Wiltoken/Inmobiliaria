"""Pytest fixtures and test environment configuration."""

from __future__ import annotations

import os

# Set test secrets BEFORE importing app.config to avoid the SECRET_KEY validator
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-256-bits-for-testing-only-!!!!!!!!")

import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import AuthSettings
from app.domain.models import Base, Role, User
from app.main import app


# --------------------------------------------------------------------------- #
# Settings fixture
# --------------------------------------------------------------------------- #


@pytest.fixture
def test_settings() -> AuthSettings:
    """Override settings for tests — uses SQLite in-memory and weak secrets."""
    return AuthSettings(
        secret_key="test-secret-key-for-testing-only-minimum-256-bits-long!!",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        recaptcha_enabled=False,
        password_min_length=8,
        password_require_special=True,
        max_login_attempts=3,
        lockout_duration_minutes=15,
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
        rate_limit_requests_per_second=10,
        rate_limit_window_seconds=1,
    )


# --------------------------------------------------------------------------- #
# Database engine + session fixtures
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def test_db(test_settings: AuthSettings) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh in-memory SQLite DB for each test.

    - Creates all tables before the test
    - Yields the session
    - Drops all tables after the test
    """
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_maker() as session:
        yield session

    await engine.dispose()


# --------------------------------------------------------------------------- #
# Overriding get_settings for tests
# --------------------------------------------------------------------------- #

# We store original settings and patch it in the app.config module
_original_settings = None


@pytest.fixture(autouse=True)
def patch_settings(test_settings: AuthSettings, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch app.config.settings and get_settings for the duration of each test."""
    import app.config as config_module

    monkeypatch.setattr(config_module, "settings", test_settings, raising=False)
    monkeypatch.setattr(config_module, "_cached_settings", test_settings, raising=False)
    # Also patch get_settings to return our test settings
    monkeypatch.setattr(config_module, "get_settings", lambda: test_settings, raising=False)


# --------------------------------------------------------------------------- #
# Async client fixture (for integration / e2e tests)
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def test_client(test_settings: AuthSettings) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient wired to the FastAPI app via ASGI transport."""
    # Patch database module to use test engine
    import app.adapters.database as db_module

    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    # Patch the engine and session maker in the database module
    original_engine = getattr(db_module, "_engine", None)
    original_session_maker = getattr(db_module, "_async_session_maker", None)

    db_module._engine = engine
    db_module._async_session_maker = session_maker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Restore original engine/session maker
    db_module._engine = original_engine
    db_module._async_session_maker = original_session_maker

    await engine.dispose()


# --------------------------------------------------------------------------- #
# User factory fixture
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user with a plain-text password of 'ValidPass1!'."""
    from app.core.security import hash_password

    user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        username="testuser",
        email="testuser@example.com",
        password_hash=hash_password("ValidPass1!"),
        is_active=True,
        is_locked=False,
        password_changed_at=datetime.now(timezone.utc),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_with_role(test_db: AsyncSession, test_user: User) -> tuple[User, Role]:
    """Create a test user and a role, then assign the role to the user."""
    role = Role(id=uuid.uuid4(), name="admin")
    test_db.add(role)
    test_user.roles.append(role)
    await test_db.commit()
    await test_db.refresh(test_user)
    return test_user, role


# --------------------------------------------------------------------------- #
# Redis mock fixture (using fakeredis)
# --------------------------------------------------------------------------- #


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Patch redis client to use fakeredis for tests that don't need real Redis."""
    import app.adapters.redis_client as redis_module
    import fakeredis.aioredis

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    # Patch get_redis_client to return fake redis
    monkeypatch.setattr(redis_module, "get_redis_client", lambda: fake, raising=False)
    yield
    # Cleanup is handled by fakeredis automatically


# --------------------------------------------------------------------------- #
# E2E test placeholder
# --------------------------------------------------------------------------- #
# NOTE: E2E tests (tests/e2e/) require a running PostgreSQL + PostGIS instance.
# They are skipped in CI/local environments that don't have the database
# available. To run E2E tests:
#   1. Start the full docker stack: docker-compose -f docker-compose.yml up -d
#   2. Run: pytest tests/e2e/ -v
#
# Current E2E test files:
#   - tests/e2e/test_auth_flow.py
#   - tests/e2e/test_lockout.py
#
# To add a new E2E test, ensure the docker stack is running and the test
# uses the real database (not SQLite).
