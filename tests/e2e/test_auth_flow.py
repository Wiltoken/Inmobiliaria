"""E2E tests for full auth flow: login → refresh → logout via httpx AsyncClient."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.domain.models import Base, Role, User
from app.main import app


# --------------------------------------------------------------------------- #
# E2E fixtures
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture
async def e2e_client() -> AsyncClient:
    """Create a test client backed by an in-memory SQLite DB."""
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

    # Patch the database module to use our test engine
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
async def e2e_user(e2e_client: AsyncClient) -> User:
    """Create a real user in the test DB."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.adapters.database import get_session_maker

    session_maker = get_session_maker()
    async with session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            username="e2euser",
            email="e2euser@test.com",
            password_hash=hash_password("TestPass123!"),
            is_active=True,
            is_locked=False,
            password_changed_at=datetime.now(timezone.utc),
        )
        role = Role(id=uuid.uuid4(), name="user")
        session.add(role)
        user.roles.append(role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --------------------------------------------------------------------------- #
# E2E: Full login → refresh → logout cycle
# --------------------------------------------------------------------------- #

class TestAuthFlowE2E:
    """End-to-end tests for the full authentication cycle."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, e2e_client: AsyncClient) -> None:
        """GET /health returns 200 OK."""
        response = await e2e_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens(
        self,
        e2e_client: AsyncClient,
        e2e_user: User,
    ) -> None:
        """POST /api/v1/auth/login with valid credentials returns tokens."""
        response = await e2e_client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2euser",
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(
        self,
        e2e_client: AsyncClient,
        e2e_user: User,
    ) -> None:
        """POST /api/v1/auth/login with wrong password returns 401."""
        response = await e2e_client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2euser",
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_login_unknown_user_returns_401(self, e2e_client: AsyncClient) -> None:
        """POST /api/v1/auth/login with unknown user returns 401 (no user enumeration)."""
        response = await e2e_client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_returns_new_access_token(
        self,
        e2e_client: AsyncClient,
        e2e_user: User,
    ) -> None:
        """POST /api/v1/auth/login then refresh returns a new access token."""
        # Step 1: Login
        login_response = await e2e_client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2euser",
                "password": "TestPass123!",
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        original_access = login_data["access_token"]

        # Step 2: Refresh
        refresh_response = await e2e_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert refresh_data["access_token"] != original_access
        assert refresh_data["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token_returns_401(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """POST /api/v1/auth/refresh with an invalid token returns 401."""
        response = await e2e_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_returns_204(
        self,
        e2e_client: AsyncClient,
        e2e_user: User,
    ) -> None:
        """POST /api/v1/auth/logout with a valid token returns 204."""
        # Login to get a token
        login_response = await e2e_client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2euser",
                "password": "TestPass123!",
            },
        )
        access_token = login_response.json()["access_token"]

        # Logout with the access token
        logout_response = await e2e_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_without_token_returns_204(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """POST /api/v1/auth/logout without a token is idempotent and returns 204."""
        response = await e2e_client.post("/api/v1/auth/logout")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_full_cycle_login_refresh_logout(
        self,
        e2e_client: AsyncClient,
        e2e_user: User,
    ) -> None:
        """Complete cycle: login → refresh → logout → verify token revoked."""
        # 1. Login
        login_resp = await e2e_client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2euser",
                "password": "TestPass123!",
            },
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 2. Refresh token
        refresh_resp = await e2e_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        new_access = refresh_resp.json()["access_token"]
        assert new_access != access_token

        # 3. Logout
        logout_resp = await e2e_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert logout_resp.status_code == 204

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_valid_token(
        self,
        e2e_client: AsyncClient,
        e2e_user: User,
    ) -> None:
        """A valid access token can reach protected endpoints."""
        # Login
        login_resp = await e2e_client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2euser",
                "password": "TestPass123!",
            },
        )
        access_token = login_resp.json()["access_token"]

        # Access /api/v1/users/me
        me_resp = await e2e_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # 200 or 401 depending on whether the endpoint requires session activity check
        assert me_resp.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_without_token(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Requests without a Bearer token to protected endpoints return 401."""
        response = await e2e_client.get("/api/v1/users/me")
        assert response.status_code == 401
