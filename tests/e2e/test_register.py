"""E2E tests for user registration: POST /api/v1/auth/register.

Covers the buyer/seller/agent flows, token issuance, and validation errors.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.domain.models import Base, Role
from app.main import app


@pytest_asyncio.fixture
async def register_client() -> AsyncClient:
    """Client backed by in-memory SQLite + fakeredis, with roles seeded."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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

    # Patch the database module to use the test engine
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

    # Seed the roles the register endpoint looks up
    async with session_maker() as session:
        for name in ("buyer", "seller", "agent"):
            session.add(Role(id=uuid.uuid4(), name=name))
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Restore
    db_module._engine = original_engine
    db_module._async_session_maker = original_session_maker
    if original_client is not None:
        redis_module._client = original_client
    await engine.dispose()


def _buyer_payload(**overrides) -> dict:
    payload = {
        "username": "comprador1",
        "email": "comprador1@example.com",
        "full_name": "Comprador Uno",
        "password": "Comprador123!",
        "role": "buyer",
        "budget_min": 200_000_000,
        "budget_max": 500_000_000,
        "preferred_locations": ["Chapinero", "Poblado"],
    }
    payload.update(overrides)
    return payload


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_buyer_success(self, register_client: AsyncClient) -> None:
        response = await register_client.post(
            "/api/v1/auth/register",
            json=_buyer_payload(),
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
        assert data["user"]["roles"][0]["name"] == "buyer"
        assert data["user"]["role_id"]
        assert data["user"]["full_name"] == "Comprador Uno"

        # Buyer profile was created
        from sqlalchemy import select

        from app.adapters.database import get_session_maker
        from app.domain.models import BuyerProfile, User

        async with get_session_maker()() as session:
            result = await session.execute(select(BuyerProfile))
            profile = result.scalar_one()
            assert profile.budget_min == 200_000_000
            assert profile.preferred_locations == [
                {"city": "Chapinero", "lat": None, "lon": None, "radius_km": 5.0},
                {"city": "Poblado", "lat": None, "lon": None, "radius_km": 5.0},
            ]

            user = (await session.execute(select(User))).scalar_one()
            assert user.full_name == "Comprador Uno"

    @pytest.mark.asyncio
    async def test_register_seller_success(self, register_client: AsyncClient) -> None:
        response = await register_client.post(
            "/api/v1/auth/register",
            json={
                "username": "vendedor1",
                "email": "vendedor1@example.com",
                "password": "Vendedor123!",
                "role": "seller",
                "phone": "+57 300 123 4567",
                "company_name": "Inmobiliaria Prime",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["user"]["roles"][0]["name"] == "seller"

        from sqlalchemy import select

        from app.adapters.database import get_session_maker
        from app.domain.models import SellerProfile

        async with get_session_maker()() as session:
            profile = (await session.execute(select(SellerProfile))).scalar_one()
            assert profile.phone == "+57 300 123 4567"
            assert profile.company_name == "Inmobiliaria Prime"

    @pytest.mark.asyncio
    async def test_register_agent_success(self, register_client: AsyncClient) -> None:
        response = await register_client.post(
            "/api/v1/auth/register",
            json={
                "username": "agente1",
                "email": "agente1@example.com",
                "password": "Agente123!",
                "role": "agent",
                "license_number": "LIC-9999",
                "agency_name": "Fincaraíz Pro",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["user"]["roles"][0]["name"] == "agent"

        from sqlalchemy import select

        from app.adapters.database import get_session_maker
        from app.domain.models import AgentProfile

        async with get_session_maker()() as session:
            profile = (await session.execute(select(AgentProfile))).scalar_one()
            assert profile.license_number == "LIC-9999"
            assert profile.agency_name == "Fincaraíz Pro"

    @pytest.mark.asyncio
    async def test_register_agent_missing_license(self, register_client: AsyncClient) -> None:
        response = await register_client.post(
            "/api/v1/auth/register",
            json={
                "username": "agente_sin_licencia",
                "email": "agente-sin-licencia@example.com",
                "password": "Agente123!",
                "role": "agent",
            },
        )
        assert response.status_code == 400
        assert response.headers["error_code"] == "AUTH_AGENT_LICENSE_REQUIRED"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, register_client: AsyncClient) -> None:
        first = await register_client.post(
            "/api/v1/auth/register",
            json=_buyer_payload(),
        )
        assert first.status_code == 201

        second = await register_client.post(
            "/api/v1/auth/register",
            json=_buyer_payload(email="otro@example.com"),
        )
        assert second.status_code == 409
        assert second.headers["error_code"] == "AUTH_USER_EXISTS"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, register_client: AsyncClient) -> None:
        first = await register_client.post(
            "/api/v1/auth/register",
            json=_buyer_payload(),
        )
        assert first.status_code == 201

        second = await register_client.post(
            "/api/v1/auth/register",
            json=_buyer_payload(username="otrousuario"),
        )
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_role(self, register_client: AsyncClient) -> None:
        response = await register_client.post(
            "/api/v1/auth/register",
            json=_buyer_payload(role="admin"),
        )
        assert response.status_code == 400
        assert response.headers["error_code"] == "AUTH_INVALID_ROLE"

    @pytest.mark.asyncio
    async def test_register_weak_password(self, register_client: AsyncClient) -> None:
        response = await register_client.post(
            "/api/v1/auth/register",
            json=_buyer_payload(password="sinmayusculas"),
        )
        assert response.status_code == 400
        assert response.headers["error_code"] == "AUTH_PASSWORD_POLICY_VIOLATION"

    @pytest.mark.asyncio
    async def test_register_then_login(self, register_client: AsyncClient) -> None:
        payload = _buyer_payload()
        register_resp = await register_client.post("/api/v1/auth/register", json=payload)
        assert register_resp.status_code == 201

        login_resp = await register_client.post(
            "/api/v1/auth/login",
            json={"username": payload["username"], "password": payload["password"]},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()
