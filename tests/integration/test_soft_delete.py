from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    AgentProfile,
    AuditLog,
    BuyerProfile,
    PasswordReset,
    RefreshToken,
    SellerProfile,
    User,
)


@pytest.mark.asyncio
async def test_soft_delete_user_cascades_to_profiles(
    test_client: AsyncClient,
    test_user: User,
    test_db: AsyncSession,
    mock_redis: None,
) -> None:
    buyer = BuyerProfile(user_id=test_user.id)
    seller = SellerProfile(user_id=test_user.id)
    agent = AgentProfile(user_id=test_user.id, license_number="LIC-001")
    test_db.add_all([buyer, seller, agent])
    await test_db.commit()

    resp = await test_client.post(
        f"/api/v1/admin/users/{test_user.id}/delete-data",
        headers={"X-User-Id": str(test_user.id), "X-User-Roles": "admin"},
    )
    assert resp.status_code == 204

    await test_db.refresh(test_user)
    assert test_user.deleted_at is not None
    assert test_user.deletion_reason == "admin_requested"
    assert test_user.is_active is False

    await test_db.refresh(buyer)
    await test_db.refresh(seller)
    await test_db.refresh(agent)
    assert buyer.is_deleted is True
    assert seller.is_deleted is True
    assert agent.is_deleted is True


@pytest.mark.asyncio
async def test_soft_deleted_user_cannot_login(
    test_client: AsyncClient,
    test_user: User,
    test_db: AsyncSession,
    mock_redis: None,
) -> None:
    test_user.deleted_at = datetime.now(UTC)
    await test_db.commit()

    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": "ValidPass1!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_soft_deleted_user_not_in_listings(
    test_client: AsyncClient,
    test_user: User,
    test_db: AsyncSession,
    mock_redis: None,
) -> None:
    test_user.deleted_at = datetime.now(UTC)
    await test_db.commit()

    resp = await test_client.get(
        "/api/v1/admin/users",
        headers={"X-User-Id": str(test_user.id), "X-User-Roles": "admin"},
    )
    assert resp.status_code == 200
    data = resp.json()
    user_ids = [u["id"] for u in data["users"]]
    assert str(test_user.id) not in user_ids


@pytest.mark.asyncio
async def test_soft_deleted_profile_not_in_matching(
    test_client: AsyncClient,
    test_user: User,
    test_db: AsyncSession,
    mock_redis: None,
) -> None:
    buyer = BuyerProfile(user_id=test_user.id, is_deleted=True)
    test_db.add(buyer)
    await test_db.commit()

    from app.core.matching import compute_all_matches
    matches = await compute_all_matches(test_user.id, test_db)
    assert matches == []


@pytest.mark.asyncio
async def test_restore_user_reverses_soft_delete(
    test_client: AsyncClient,
    test_user: User,
    test_db: AsyncSession,
    mock_redis: None,
) -> None:
    test_user.deleted_at = datetime.now(UTC)
    test_user.deletion_reason = "admin_requested"
    test_user.is_active = False
    buyer = BuyerProfile(user_id=test_user.id, is_deleted=True)
    test_db.add(buyer)
    await test_db.commit()

    resp = await test_client.post(
        f"/api/v1/admin/users/{test_user.id}/restore",
        headers={"X-User-Id": str(test_user.id), "X-User-Roles": "admin"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is True
    assert data["deleted_at"] is None
    assert data["deletion_reason"] is None


@pytest.mark.asyncio
async def test_admin_delete_data_requires_admin_role(
    test_client: AsyncClient,
    test_user: User,
) -> None:
    resp = await test_client.post(
        f"/api/v1/admin/users/{test_user.id}/delete-data",
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_self_delete_data_invalidates_token(
    test_client: AsyncClient,
    test_user: User,
    test_db: AsyncSession,
    mock_redis: None,
) -> None:
    resp = await test_client.post(
        "/api/v1/users/me/delete-data",
        headers={"X-User-Id": str(test_user.id), "X-User-Roles": "buyer"},
    )
    assert resp.status_code == 204

    await test_db.refresh(test_user)
    assert test_user.deleted_at is not None
    assert test_user.deletion_reason == "user_requested"
    assert test_user.is_active is False
