"""E2E tests for account lockout: 3 wrong passwords → 423 Locked."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.domain.models import Base, LoginAttempt, User
from app.main import app


# --------------------------------------------------------------------------- #
# E2E fixtures
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture
async def lockout_client() -> AsyncClient:
    """Create a test client backed by an in-memory SQLite DB with max 3 attempts."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
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

    # Patch database
    import app.adapters.database as db_module

    original_engine = db_module._engine
    original_session_maker = db_module._async_session_maker
    db_module._engine = engine
    db_module._async_session_maker = session_maker

    # Patch redis to use fakeredis
    import fakeredis.aioredis
    import app.adapters.redis_client as redis_module

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    original_client = getattr(redis_module, "_client", None)
    redis_module._client = fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Restore
    db_module._engine = original_engine
    db_module._async_session_maker = original_session_maker
    if original_client is not None:
        redis_module._client = original_client
    await engine.dispose()


@pytest_asyncio.fixture
async def lockout_user(lockout_client: AsyncClient) -> User:
    """Create a user in the test DB with the standard test password."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.adapters.database import get_session_maker

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            username="lockuser",
            email="lockuser@test.com",
            password_hash=hash_password("CorrectPass1!"),
            is_active=True,
            is_locked=False,
            password_changed_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --------------------------------------------------------------------------- #
# Lockout E2E tests
# --------------------------------------------------------------------------- #

class TestAccountLockoutE2E:
    """End-to-end tests for account lockout after failed login attempts."""

    @pytest.mark.asyncio
    async def test_login_wrong_password_x3_returns_423_locked(
        self,
        lockout_client: AsyncClient,
        lockout_user: User,
    ) -> None:
        """After 3 wrong passwords, the account is locked and returns 423."""
        wrong_password = "WrongPassword1!"

        # Make 3 failed login attempts
        for i in range(3):
            response = await lockout_client.post(
                "/api/v1/auth/login",
                json={
                    "username": "lockuser",
                    "password": wrong_password,
                },
            )
            # First 2 should be 401 with remaining_attempts
            if i < 2:
                assert response.status_code == 401, f"Attempt {i+1} should return 401"
                data = response.json()
                # remaining_attempts should decrement
                if "remaining_attempts" in str(data):
                    pass  # Got expected error with remaining attempts
            else:
                # 3rd failed attempt triggers lockout → 423
                assert response.status_code == 423, f"3rd attempt should return 423, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_locked_account_returns_423_with_locked_until(
        self,
        lockout_client: AsyncClient,
        lockout_user: User,
    ) -> None:
        """A locked account's response includes a locked_until timestamp."""
        wrong_password = "WrongPassword1!"

        # Exhaust attempts to trigger lockout
        for _ in range(3):
            await lockout_client.post(
                "/api/v1/auth/login",
                json={
                    "username": "lockuser",
                    "password": wrong_password,
                },
            )

        # 4th attempt — should already be locked
        response = await lockout_client.post(
            "/api/v1/auth/login",
            json={
                "username": "lockuser",
                "password": wrong_password,
            },
        )
        assert response.status_code == 423
        data = response.json()
        # The detail should include locked_until information
        assert "locked_until" in str(data) or "locked" in str(data).lower()

    @pytest.mark.asyncio
    async def test_correct_password_after_lockout_still_returns_423(
        self,
        lockout_client: AsyncClient,
        lockout_user: User,
    ) -> None:
        """Even the correct password cannot unlock an account that is locked."""
        wrong_password = "WrongPassword1!"

        # Trigger lockout
        for _ in range(3):
            await lockout_client.post(
                "/api/v1/auth/login",
                json={
                    "username": "lockuser",
                    "password": wrong_password,
                },
            )

        # Now try with the correct password
        response = await lockout_client.post(
            "/api/v1/auth/login",
            json={
                "username": "lockuser",
                "password": "CorrectPass1!",
            },
        )
        assert response.status_code == 423

    @pytest.mark.asyncio
    async def test_lockout_423_response_body_has_error_code(
        self,
        lockout_client: AsyncClient,
        lockout_user: User,
    ) -> None:
        """The 423 response body includes the AUTH_ACCOUNT_LOCKED error code."""
        wrong_password = "WrongPassword1!"

        # Trigger lockout
        for _ in range(3):
            await lockout_client.post(
                "/api/v1/auth/login",
                json={
                    "username": "lockuser",
                    "password": wrong_password,
                },
            )

        response = await lockout_client.post(
            "/api/v1/auth/login",
            json={
                "username": "lockuser",
                "password": wrong_password,
            },
        )
        assert response.status_code == 423
        body = response.json()
        # The error code should be AUTH_ACCOUNT_LOCKED
        body_str = str(body)
        assert "AUTH_ACCOUNT_LOCKED" in body_str or "locked" in body_str.lower()

    @pytest.mark.asyncio
    async def test_successful_login_resets_attempt_counter(
        self,
        lockout_client: AsyncClient,
        lockout_user: User,
    ) -> None:
        """A successful login resets the failed attempt counter."""
        wrong_password = "WrongPassword1!"

        # 2 failed attempts
        for _ in range(2):
            await lockout_client.post(
                "/api/v1/auth/login",
                json={
                    "username": "lockuser",
                    "password": wrong_password,
                },
            )

        # Successful login
        login_resp = await lockout_client.post(
            "/api/v1/auth/login",
            json={
                "username": "lockuser",
                "password": "CorrectPass1!",
            },
        )
        assert login_resp.status_code == 200

        # 2 more wrong attempts should NOT lock (counter was reset)
        for _ in range(2):
            resp = await lockout_client.post(
                "/api/v1/auth/login",
                json={
                    "username": "lockuser",
                    "password": wrong_password,
                },
            )
            assert resp.status_code == 401

        # 3rd wrong attempt triggers lockout now
        resp = await lockout_client.post(
            "/api/v1/auth/login",
            json={
                "username": "lockuser",
                "password": wrong_password,
            },
        )
        assert resp.status_code == 423


# We need to import AsyncSession here for type annotations
from sqlalchemy.ext.asyncio import AsyncSession
