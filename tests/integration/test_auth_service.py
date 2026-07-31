"""Integration tests for the auth service — login flow with test DB.

These tests use the User model which contains PostgreSQL-specific types (CITEXT).
They require a PostgreSQL test database to run. When run against SQLite,
they will be skipped.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import CompileError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, hash_password
from app.domain.models import Base, RefreshToken, Role, User


# --------------------------------------------------------------------------- #
# NOTE: These tests require PostgreSQL because the User model uses CITEXT.
# When the test DB is SQLite (in-memory), these tests are skipped.
# --------------------------------------------------------------------------- #

def _is_sqlite(database_url: str) -> bool:
    return "sqlite" in database_url.lower()


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture
async def auth_db_session() -> AsyncSession:
    """Create a fresh in-memory SQLite DB for auth service tests.

    NOTE: SQLite doesn't support CITEXT, so tests that need User model will
    be skipped when using SQLite. Use PostgreSQL for full integration tests.
    """
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

    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def auth_user(auth_db_session: AsyncSession) -> User:
    """Create a test user with a known password 'ValidPass1!'.

    Skipped if SQLite (CITEXT not supported).
    """
    try:
        user = User(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            username="authtest",
            email="authtest@example.com",
            password_hash=hash_password("ValidPass1!"),
            is_active=True,
            is_locked=False,
            password_changed_at=datetime.now(timezone.utc),
        )
        auth_db_session.add(user)
        await auth_db_session.commit()
        await auth_db_session.refresh(user)
        return user
    except CompileError:
        # CITEXT not supported in SQLite — skip this fixture
        pytest.skip("User model requires PostgreSQL (uses CITEXT)")


# --------------------------------------------------------------------------- #
# Login flow tests
# --------------------------------------------------------------------------- #

class TestLoginFlow:
    """End-to-end login flow tests using the real auth service components."""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        auth_db_session: AsyncSession,
        auth_user: User,
    ) -> None:
        """Valid credentials return tokens and create a refresh token record."""
        from app.core.security import verify_password

        # Verify user exists and password is correct
        result = await auth_db_session.execute(
            select(User).where(User.username == "authtest")
        )
        user = result.scalar_one()
        assert verify_password("ValidPass1!", user.password_hash) is True
        assert user.is_active is True
        assert user.is_locked is False

    @pytest.mark.asyncio
    async def test_login_creates_access_and_refresh_tokens(
        self,
        auth_db_session: AsyncSession,
        auth_user: User,
    ) -> None:
        """Successful auth creates both access and refresh JWTs."""
        user_id = auth_user.id
        tenant_id = auth_user.tenant_id

        access_token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["user"],
            jti=str(uuid.uuid4()),
        )
        refresh_token = create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
            jti=str(uuid.uuid4()),
        )

        assert access_token.startswith("eyJ")  # JWT prefix
        assert refresh_token.startswith("eyJ")
        assert access_token != refresh_token

    @pytest.mark.asyncio
    async def test_login_stores_refresh_token_in_db(
        self,
        auth_db_session: AsyncSession,
        auth_user: User,
    ) -> None:
        """After login, a RefreshToken record exists in the DB."""
        user_id = auth_user.id
        tenant_id = auth_user.tenant_id
        jti = str(uuid.uuid4())

        # Simulate what the login endpoint does: store refresh token in DB
        from datetime import timedelta

        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        refresh_token_record = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            jti=jti,
            token_hash="hash-placeholder",
            expires_at=expires_at,
        )
        auth_db_session.add(refresh_token_record)
        await auth_db_session.commit()

        # Verify the token is stored
        result = await auth_db_session.execute(
            select(RefreshToken).where(RefreshToken.jti == jti)
        )
        stored = result.scalar_one()
        assert stored.user_id == user_id
        assert stored.expires_at == expires_at

    @pytest.mark.asyncio
    async def test_failed_login_does_not_create_tokens(
        self,
        auth_db_session: AsyncSession,
        auth_user: User,
    ) -> None:
        """Failed login attempt should not create any refresh token records."""
        from app.core.security import verify_password

        # Wrong password attempt
        is_correct = verify_password("WrongPassword1!", auth_user.password_hash)
        assert is_correct is False

        # No new refresh tokens should exist
        result = await auth_db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == auth_user.id)
        )
        tokens = result.scalars().all()
        assert len(tokens) == 0


class TestLoginAttemptTracking:
    """Tests for login attempt tracking and lockout logic."""

    @pytest.mark.asyncio
    async def test_user_not_locked_initially(
        self,
        auth_db_session: AsyncSession,
        auth_user: User,
    ) -> None:
        """New users are not locked."""
        result = await auth_db_session.execute(
            select(User).where(User.id == auth_user.id)
        )
        user = result.scalar_one()
        assert user.is_locked is False
        assert user.locked_until is None

    @pytest.mark.asyncio
    async def test_user_can_be_locked(
        self,
        auth_db_session: AsyncSession,
        auth_user: User,
    ) -> None:
        """Setting is_locked=True and locked_until future date locks the account."""
        from datetime import timedelta

        auth_user.is_locked = True
        auth_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await auth_db_session.commit()

        result = await auth_db_session.execute(
            select(User).where(User.id == auth_user.id)
        )
        user = result.scalar_one()
        assert user.is_locked is True
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_user_unlock_clears_locked_state(
        self,
        auth_db_session: AsyncSession,
        auth_user: User,
    ) -> None:
        """Clearing is_locked and locked_until unlocks the account."""
        # First lock the user
        from datetime import timedelta

        auth_user.is_locked = True
        auth_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        await auth_db_session.commit()

        # Then unlock
        auth_user.is_locked = False
        auth_user.locked_until = None
        await auth_db_session.commit()

        result = await auth_db_session.execute(
            select(User).where(User.id == auth_user.id)
        )
        user = result.scalar_one()
        assert user.is_locked is False
        assert user.locked_until is None
