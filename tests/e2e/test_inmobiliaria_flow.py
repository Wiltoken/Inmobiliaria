"""E2E tests for the full inmobiliaria platform journey.

Full journey covered:
  1. Register buyer + seller (with roles)
  2. Seller publishes a property
  3. Buyer creates an inquiry on that property
  4. Seller responds to the inquiry (accept / decline / request_more_info)
  5. Notification dispatch is asserted via SMTP mock

Coverage: REQ-INMO-001, REQ-INMO-010, REQ-INMO-021, REQ-INMO-030,
          REQ-INMO-031, REQ-INMO-032, REQ-INMO-034.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.domain.models import (
    Base,
    BuyerProfile,
    Inquiry,
    InquiryStatus,
    Role,
    SellerProfile,
    User,
)
from app.main import app

# --------------------------------------------------------------------------- #
# E2E test fixtures (SQLite in-memory + mocked SMTP)
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def e2e_client() -> AsyncClient:
    """AsyncClient backed by a fresh in-memory SQLite DB."""
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    db_module._engine = original_engine
    db_module._async_session_maker = original_session_maker
    if original_client is not None:
        redis_module._client = original_client
    await engine.dispose()


async def _create_user(
    _session_maker,  # unused — kept for API compat
    username: str,
    email: str,
    role_name: str,
    password: str = "ValidPass1!",
) -> tuple[User, str]:
    """Create a user with a role using the e2e_client's engine and return (user, access_token)."""
    import app.adapters.database as db_module

    user_id = uuid.uuid4()
    role_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    async with db_module._async_session_maker() as session:
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_locked=False,
            password_changed_at=datetime.now(timezone.utc),
        )
        role = Role(id=role_id, name=role_name)
        session.add(role)
        user.roles.append(role)

        if role_name == "buyer":
            profile = BuyerProfile(
                id=uuid.uuid4(),
                budget_min=50_000_000,
                budget_max=200_000_000,
            )
            session.add(profile)
            user.buyer_profile = profile
        elif role_name == "seller":
            profile = SellerProfile(
                id=uuid.uuid4(),
                phone="+573001234567",
            )
            session.add(profile)
            user.seller_profile = profile

        session.add(user)
        await session.commit()

    # Get access token via login
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert login_resp.status_code == 200, f"Login failed for {username}: {login_resp.text}"
        access_token = login_resp.json()["access_token"]

    return user, access_token


# --------------------------------------------------------------------------- #
# T-3.1: Full journey test
# --------------------------------------------------------------------------- #


class TestInmobiliariaFlowE2E:
    """End-to-end journey tests for the inmobiliaria platform."""

    @pytest.mark.asyncio
    async def test_full_journey_seller_publishes_buyer_inquires_seller_responds(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Complete journey: seller publishes → buyer inquiries → seller responds.

        Covers:
        - Seller creates and publishes a property
        - Buyer creates an inquiry
        - Seller responds (accept) to the inquiry
        - Inquiry status transitions are correct
        """
        # Step 1: Create seller and buyer users
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="seller_e2e",
            email="seller_e2e@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="buyer_e2e",
            email="buyer_e2e@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        # Step 2: Seller publishes a property
        publish_resp = await e2e_client.post(
            "/api/v1/properties",
            headers=headers_seller,
            json={
                "type": "apartment",
                "operation": "sale",
                "price": 150_000_000,
                "area_m2": 75.0,
                "lat": 4.7110,
                "lon": -74.0721,
                "rooms": 3,
                "bathrooms": 2,
                "features": ["gimnasio", "piscina"],
                "title": "Hermoso apartamento en Bogotá",
                "description": "Amplio apartamento con vista a la ciudad",
            },
        )
        assert publish_resp.status_code == 201, f"Publish failed: {publish_resp.text}"
        property_data = publish_resp.json()
        property_id = property_data["id"]
        assert property_data["status"] == "active"

        # Step 3: Buyer creates an inquiry
        inquiry_resp = await e2e_client.post(
            "/api/v1/inquiries",
            headers=headers_buyer,
            json={
                "property_id": property_id,
                "message": "Me interesa este apartamento. ¿Podemos agendar una visita?",
                "contact_preference": "email",
            },
        )
        assert inquiry_resp.status_code == 201, f"Inquiry creation failed: {inquiry_resp.text}"
        inquiry_data = inquiry_resp.json()
        assert inquiry_data["status"] == "pending"
        assert inquiry_data["from_user_id"] == str(buyer.id)
        assert inquiry_data["property_id"] == property_id

        inquiry_id = inquiry_data["id"]

        # Step 4: Seller accepts the inquiry
        accept_resp = await e2e_client.patch(
            f"/api/v1/inquiries/{inquiry_id}",
            headers=headers_seller,
            json={
                "action": "accept",
                "response_message": "¡Por supuesto! Podemos agendar una visita el sábado.",
            },
        )
        assert accept_resp.status_code == 200, f"Accept failed: {accept_resp.text}"
        updated = accept_resp.json()
        assert updated["status"] == "interested"

        # Step 5: Verify seller can see the received inquiry
        received_resp = await e2e_client.get(
            "/api/v1/inquiries/received",
            headers=headers_seller,
        )
        assert received_resp.status_code == 200
        received = received_resp.json()
        assert received["total"] >= 1
        inquiry_ids = [i["id"] for i in received["inquiries"]]
        assert inquiry_id in inquiry_ids

        # Step 6: Verify buyer can see the sent inquiry
        sent_resp = await e2e_client.get(
            "/api/v1/inquiries/sent",
            headers=headers_buyer,
        )
        assert sent_resp.status_code == 200
        sent = sent_resp.json()
        assert sent["total"] >= 1
        sent_ids = [i["id"] for i in sent["inquiries"]]
        assert inquiry_id in sent_ids


# --------------------------------------------------------------------------- #
# T-3.2: Notification dispatch assertion
# --------------------------------------------------------------------------- #


class TestInquiryNotificationsE2E:
    """E2E tests verifying SMTP notifications are dispatched correctly."""

    @pytest.mark.asyncio
    async def test_seller_receives_email_notification_on_inquiry_creation(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """When buyer creates an inquiry, owner receives an email notification.

        REQ-INMO-034: Property owner must be notified on new inquiry.
        """
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="notif_seller",
            email="notif_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="notif_buyer",
            email="notif_buyer@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        # Seller publishes a property
        publish_resp = await e2e_client.post(
            "/api/v1/properties",
            headers=headers_seller,
            json={
                "type": "house",
                "operation": "sale",
                "price": 350_000_000,
                "area_m2": 120.0,
                "title": "Casa en Chico",
                "description": "Casa amplia en zona residencial",
            },
        )
        assert publish_resp.status_code == 201
        property_id = publish_resp.json()["id"]

        # Mock SMTP before creating inquiry
        with patch("app.core.notifications._send_smtp_email") as mock_send:
            mock_send.return_value = None

            inquiry_resp = await e2e_client.post(
                "/api/v1/inquiries",
                headers=headers_buyer,
                json={
                    "property_id": property_id,
                    "message": "¿Está disponible para visita mañana?",
                    "contact_preference": "email",
                },
            )
            assert inquiry_resp.status_code == 201

            # Assert SMTP was called with seller's email
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args is not None
            assert call_args[0][0] == "notif_seller@test.com"
            assert "Casa en Chico" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_buyer_receives_email_notification_on_seller_accept(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """When seller accepts an inquiry, buyer receives an email notification.

        REQ-INMO-032: Buyer must be notified when owner responds.
        """
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="accept_seller",
            email="accept_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="accept_buyer",
            email="accept_buyer@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        # Seller publishes
        prop_resp = await e2e_client.post(
            "/api/v1/properties",
            headers=headers_seller,
            json={
                "type": "apartment",
                "operation": "rent",
                "price": 2_500_000,
                "title": "Apartamento amoblado",
                "description": "Hermoso apartamento amoblado centro",
            },
        )
        assert prop_resp.status_code == 201
        property_id = prop_resp.json()["id"]

        # Buyer creates inquiry
        inquiry_resp = await e2e_client.post(
            "/api/v1/inquiries",
            headers=headers_buyer,
            json={
                "property_id": property_id,
                "message": "Quisiera información sobre el apartamento.",
                "contact_preference": "email",
            },
        )
        assert inquiry_resp.status_code == 201
        inquiry_id = inquiry_resp.json()["id"]

        # Seller accepts — buyer should be notified
        with patch("app.core.notifications._send_smtp_email") as mock_send:
            mock_send.return_value = None

            accept_resp = await e2e_client.patch(
                f"/api/v1/inquiries/{inquiry_id}",
                headers=headers_seller,
                json={
                    "action": "accept",
                    "response_message": "Sí, está disponible. ¿Cuándo puede visitarlo?",
                },
            )
            assert accept_resp.status_code == 200

            # Assert buyer's email was notified
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args is not None
            assert call_args[0][0] == "accept_buyer@test.com"
            assert "apartamento amoblado" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_buyer_receives_email_notification_on_seller_decline(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """When seller declines, buyer receives email notification."""
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="decline_seller",
            email="decline_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="decline_buyer",
            email="decline_buyer@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        # Seller publishes
        prop_resp = await e2e_client.post(
            "/api/v1/properties",
            headers=headers_seller,
            json={
                "type": "land",
                "operation": "sale",
                "price": 500_000_000,
                "title": "Lote en Cajicá",
                "description": "Lote de 500m2",
            },
        )
        assert prop_resp.status_code == 201
        property_id = prop_resp.json()["id"]

        # Buyer creates inquiry
        inquiry_resp = await e2e_client.post(
            "/api/v1/inquiries",
            headers=headers_buyer,
            json={
                "property_id": property_id,
                "message": "Me interesa el lote.",
                "contact_preference": "email",
            },
        )
        assert inquiry_resp.status_code == 201
        inquiry_id = inquiry_resp.json()["id"]

        # Seller declines
        with patch("app.core.notifications._send_smtp_email") as mock_send:
            mock_send.return_value = None

            decline_resp = await e2e_client.patch(
                f"/api/v1/inquiries/{inquiry_id}",
                headers=headers_seller,
                json={
                    "action": "decline",
                    "response_message": "Lo sentimos, el lote ya no está disponible.",
                },
            )
            assert decline_resp.status_code == 200
            assert decline_resp.json()["status"] == "not_interested"

            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args is not None
            assert call_args[0][0] == "decline_buyer@test.com"
            assert "lote en cajicá" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_inquiry_on_own_property_is_rejected(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Buyer cannot create an inquiry on their own property (REQ-INMO-030)."""
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="own_prop_seller",
            email="own_prop@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="own_prop_buyer",
            email="own_prop_buyer@test.com",
            role_name="buyer",
        )

        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        # Seller publishes
        prop_resp = await e2e_client.post(
            "/api/v1/properties",
            headers=headers_seller,
            json={
                "type": "apartment",
                "operation": "sale",
                "price": 100_000_000,
                "title": "Apartamento propio",
                "description": "Este apt me pertenece",
            },
        )
        assert prop_resp.status_code == 201
        property_id = prop_resp.json()["id"]

        # Same seller tries to inquire on their own property
        own_inquiry_resp = await e2e_client.post(
            "/api/v1/inquiries",
            headers=headers_seller,
            json={
                "property_id": property_id,
                "message": "¿Puedo saber más de mi propio apartamento?",
                "contact_preference": "email",
            },
        )
        assert own_inquiry_resp.status_code == 400
        assert "own" in own_inquiry_resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_inquiry_on_unpublished_property_is_rejected(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Buyer cannot inquire on a non-published property (REQ-INMO-030)."""
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="unpub_seller",
            email="unpub_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="unpub_buyer",
            email="unpub_buyer@test.com",
            role_name="buyer",
        )

        headers_seller = {"Authorization": f"Bearer {seller_token}"}
        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}

        # Seller publishes a property
        prop_resp = await e2e_client.post(
            "/api/v1/properties",
            headers=headers_seller,
            json={
                "type": "apartment",
                "operation": "sale",
                "price": 100_000_000,
                "title": "Unpublished test property",
                "description": "This will be withdrawn",
            },
        )
        assert prop_resp.status_code == 201
        property_id = prop_resp.json()["id"]

        # Seller withdraws the property
        status_resp = await e2e_client.patch(
            f"/api/v1/properties/{property_id}/status",
            headers=headers_seller,
            json={"status": "withdrawn"},
        )
        assert status_resp.status_code == 200

        # Buyer tries to inquire on withdrawn property → rejected
        inquiry_resp = await e2e_client.post(
            "/api/v1/inquiries",
            headers=headers_buyer,
            json={
                "property_id": property_id,
                "message": "Is this property still available?",
                "contact_preference": "email",
            },
        )
        assert inquiry_resp.status_code == 400
        assert "published" in inquiry_resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_status_transition_rejected(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Responding to a closed inquiry is rejected (REQ-INMO-031)."""
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="closed_seller",
            email="closed_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="closed_buyer",
            email="closed_buyer@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        with patch("app.core.notifications._send_smtp_email"):
            # Seller publishes
            prop_resp = await e2e_client.post(
                "/api/v1/properties",
                headers=headers_seller,
                json={
                    "type": "apartment",
                    "operation": "sale",
                    "price": 100_000_000,
                    "title": "Closed inquiry test",
                    "description": "Testing closed inquiry guard",
                },
            )
            assert prop_resp.status_code == 201
            property_id = prop_resp.json()["id"]

            # Buyer creates inquiry
            inquiry_resp = await e2e_client.post(
                "/api/v1/inquiries",
                headers=headers_buyer,
                json={
                    "property_id": property_id,
                    "message": "Testing closed inquiry.",
                    "contact_preference": "email",
                },
            )
            assert inquiry_resp.status_code == 201
            inquiry_id = inquiry_resp.json()["id"]

        # Close the inquiry directly via DB
        import app.adapters.database as db_module

        async with db_module._async_session_maker() as session:
            result = await session.execute(
                select(Inquiry).where(Inquiry.id == uuid.UUID(inquiry_id))
            )
            inquiry = result.scalar_one()
            inquiry.status = InquiryStatus.CLOSED
            await session.commit()

        # Try to respond to closed inquiry → 400
        close_resp = await e2e_client.patch(
            f"/api/v1/inquiries/{inquiry_id}",
            headers=headers_seller,
            json={
                "action": "accept",
                "response_message": "This should fail.",
            },
        )
        assert close_resp.status_code == 400
        assert "closed" in close_resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_respond_with_request_more_info(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Seller responds with request_more_info action (REQ-INMO-031)."""
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="moreinfo_seller",
            email="moreinfo_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="moreinfo_buyer",
            email="moreinfo_buyer@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        with patch("app.core.notifications._send_smtp_email"):
            prop_resp = await e2e_client.post(
                "/api/v1/properties",
                headers=headers_seller,
                json={
                    "type": "apartment",
                    "operation": "sale",
                    "price": 100_000_000,
                    "title": "Request more info test",
                    "description": "Testing request more info",
                },
            )
            assert prop_resp.status_code == 201
            property_id = prop_resp.json()["id"]

            inquiry_resp = await e2e_client.post(
                "/api/v1/inquiries",
                headers=headers_buyer,
                json={
                    "property_id": property_id,
                    "message": "Tell me more.",
                    "contact_preference": "email",
                },
            )
            assert inquiry_resp.status_code == 201
            inquiry_id = inquiry_resp.json()["id"]

            info_resp = await e2e_client.patch(
                f"/api/v1/inquiries/{inquiry_id}",
                headers=headers_seller,
                json={
                    "action": "request_more_info",
                    "response_message": "What is your budget?",
                },
            )
            assert info_resp.status_code == 200
            assert info_resp.json()["status"] == "replied"

    @pytest.mark.asyncio
    async def test_filter_inquiries_by_status(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Inquiries can be filtered by status parameter."""
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="statusfilter_seller",
            email="statusfilter_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="statusfilter_buyer",
            email="statusfilter_buyer@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        with patch("app.core.notifications._send_smtp_email"):
            # Create 2 properties and 2 inquiries
            for i in range(2):
                prop_resp = await e2e_client.post(
                    "/api/v1/properties",
                    headers=headers_seller,
                    json={
                        "type": "apartment",
                        "operation": "sale",
                        "price": 100_000_000 + i,
                        "title": f"Filter test property {i}",
                        "description": f"Testing filters {i}",
                    },
                )
                assert prop_resp.status_code == 201
                prop_id = prop_resp.json()["id"]

                inquiry_resp = await e2e_client.post(
                    "/api/v1/inquiries",
                    headers=headers_buyer,
                    json={
                        "property_id": prop_id,
                        "message": f"Inquiry about property {i}",
                        "contact_preference": "email",
                    },
                )
                assert inquiry_resp.status_code == 201

            # Respond to first inquiry (accept) to change its status
            all_resp = await e2e_client.get(
                "/api/v1/inquiries",
                headers=headers_seller,
            )
            all_data = all_resp.json()
            assert all_data["total"] >= 2
            first_inquiry_id = all_data["inquiries"][0]["id"]

            accept_resp = await e2e_client.patch(
                f"/api/v1/inquiries/{first_inquiry_id}",
                headers=headers_seller,
                json={
                    "action": "accept",
                    "response_message": "Let's schedule a visit.",
                },
            )
            assert accept_resp.status_code == 200

        # Filter by pending — should get 1
        pending_resp = await e2e_client.get(
            "/api/v1/inquiries?status=pending",
            headers=headers_seller,
        )
        pending_data = pending_resp.json()
        assert pending_data["total"] == 1
        assert pending_data["inquiries"][0]["status"] == "pending"

        # Filter by interested — should get 1
        interested_resp = await e2e_client.get(
            "/api/v1/inquiries?status=interested",
            headers=headers_seller,
        )
        interested_data = interested_resp.json()
        assert interested_data["total"] == 1
        assert interested_data["inquiries"][0]["status"] == "interested"

    @pytest.mark.asyncio
    async def test_notification_skipped_when_contact_preference_is_phone(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """When contact_preference=phone, email notification is skipped (REQ-INMO-034)."""
        seller, seller_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="phone_seller",
            email="phone_seller@test.com",
            role_name="seller",
        )
        buyer, buyer_token = await _create_user(
            e2e_client,  # type: ignore[arg-type]
            username="phone_buyer",
            email="phone_buyer@test.com",
            role_name="buyer",
        )

        headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
        headers_seller = {"Authorization": f"Bearer {seller_token}"}

        # Seller publishes
        prop_resp = await e2e_client.post(
            "/api/v1/properties",
            headers=headers_seller,
            json={
                "type": "apartment",
                "operation": "sale",
                "price": 100_000_000,
                "title": "Apartment for phone inquiry",
            },
        )
        assert prop_resp.status_code == 201
        property_id = prop_resp.json()["id"]

        # Buyer creates inquiry with phone-only preference
        with patch("app.core.notifications._send_smtp_email") as mock_send:
            mock_send.return_value = None

            inquiry_resp = await e2e_client.post(
                "/api/v1/inquiries",
                headers=headers_buyer,
                json={
                    "property_id": property_id,
                    "message": "Prefiero que me llamen.",
                    "contact_preference": "phone",
                },
            )
            assert inquiry_resp.status_code == 201

            # SMTP should NOT be called for phone preference
            mock_send.assert_not_called()
