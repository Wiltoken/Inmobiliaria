"""E2E tests for the admin user CRUD endpoints (/api/v1/admin/users)."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.domain.models import Base, Role, User
from app.main import app


@pytest_asyncio.fixture
async def admin_client() -> AsyncClient:
    """Client backed by SQLite + fakeredis, with roles + an admin user seeded."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import DEFAULT_TENANT_ID
    from app.core.security import hash_password

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    import app.adapters.database as db_module

    original_engine = db_module._engine
    original_session_maker = db_module._async_session_maker
    db_module._engine = engine
    db_module._async_session_maker = session_maker

    import fakeredis.aioredis

    import app.adapters.redis_client as redis_module

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    original_client = getattr(redis_module, "_client", None)
    redis_module._client = fake_redis

    # Seed roles + admin user
    async with session_maker() as session:
        roles: dict[str, Role] = {}
        for name in ("buyer", "seller", "agent", "super_admin"):
            role = Role(id=uuid.uuid4(), name=name)
            session.add(role)
            roles[name] = role
        admin = User(
            id=uuid.uuid4(),
            username="admin",
            email="admin@test.com",
            password_hash=hash_password("Admin123!"),
            tenant_id=DEFAULT_TENANT_ID,
            is_active=True,
        )
        admin.roles.append(roles["super_admin"])
        session.add(admin)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    db_module._engine = original_engine
    db_module._async_session_maker = original_session_maker
    if original_client is not None:
        redis_module._client = original_client
    await engine.dispose()


async def _admin_token(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAdminUserCRUD:
    @pytest.mark.asyncio
    async def test_create_user(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        resp = await admin_client.post(
            "/api/v1/admin/users",
            json={
                "username": "nuevoagente",
                "email": "nuevoagente@test.com",
                "full_name": "Nuevo Agente",
                "password": "Agente123!",
                "role": "agent",
            },
            headers=_headers(token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["username"] == "nuevoagente"
        assert data["email"] == "nuevoagente@test.com"
        assert data["full_name"] == "Nuevo Agente"
        assert data["roles"][0]["name"] == "agent"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        payload = {
            "username": "dupuser",
            "email": "dup@test.com",
            "password": "DupUser123!",
            "role": "buyer",
        }
        first = await admin_client.post("/api/v1/admin/users", json=payload, headers=_headers(token))
        assert first.status_code == 201
        second = await admin_client.post(
            "/api/v1/admin/users",
            json={**payload, "email": "otro@test.com"},
            headers=_headers(token),
        )
        assert second.status_code == 409
        assert second.headers["error_code"] == "AUTH_USER_EXISTS"

    @pytest.mark.asyncio
    async def test_create_user_invalid_role(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        resp = await admin_client.post(
            "/api/v1/admin/users",
            json={
                "username": "badrole",
                "email": "badrole@test.com",
                "password": "BadRole123!",
                "role": "nonexistent",
            },
            headers=_headers(token),
        )
        assert resp.status_code == 400
        assert resp.headers["error_code"] == "AUTH_INVALID_ROLE"

    @pytest.mark.asyncio
    async def test_list_users(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        resp = await admin_client.get("/api/v1/admin/users", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert "users" in data
        usernames = [u["username"] for u in data["users"]]
        assert "admin" in usernames

    @pytest.mark.asyncio
    async def test_get_single_user(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        list_resp = await admin_client.get("/api/v1/admin/users", headers=_headers(token))
        user_id = list_resp.json()["users"][0]["id"]
        resp = await admin_client.get(f"/api/v1/admin/users/{user_id}", headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == user_id

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        resp = await admin_client.get(
            f"/api/v1/admin/users/{uuid.uuid4()}", headers=_headers(token)
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        # Create a user to update
        create = await admin_client.post(
            "/api/v1/admin/users",
            json={"username": "toupdate", "email": "toupdate@test.com", "password": "Update123!", "role": "buyer"},
            headers=_headers(token),
        )
        assert create.status_code == 201
        user_id = create.json()["id"]

        resp = await admin_client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"full_name": "Nombre Actualizado", "is_active": False, "roles": ["seller"]},
            headers=_headers(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["full_name"] == "Nombre Actualizado"
        assert data["is_active"] is False
        assert data["roles"][0]["name"] == "seller"

    @pytest.mark.asyncio
    async def test_delete_and_restore_user(self, admin_client: AsyncClient) -> None:
        token = await _admin_token(admin_client)
        create = await admin_client.post(
            "/api/v1/admin/users",
            json={"username": "todelete", "email": "todelete@test.com", "password": "Delete123!", "role": "buyer"},
            headers=_headers(token),
        )
        user_id = create.json()["id"]

        delete = await admin_client.post(
            f"/api/v1/admin/users/{user_id}/delete-data", headers=_headers(token)
        )
        assert delete.status_code == 204

        # Restore
        restore = await admin_client.post(
            f"/api/v1/admin/users/{user_id}/restore", headers=_headers(token)
        )
        assert restore.status_code == 200
        assert restore.json()["is_active"] is True
        assert restore.json()["deleted_at"] is None
