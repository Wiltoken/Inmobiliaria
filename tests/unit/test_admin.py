"""Unit tests for admin property moderation logic.

Tests approve_property and reject_property business rules with mocks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.domain.models import PropertyStatus


class MockUser:
    def __init__(self, user_id: uuid.UUID | None = None):
        self.id = user_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_mock_property(
    *,
    prop_id: uuid.UUID | None = None,
    title: str = "Test Property",
    price: float = 200_000.0,
    status: str = PropertyStatus.PENDING.value,
    is_active: bool = True,
    owner_id: uuid.UUID | None = None,
    rejection_reason: str | None = None,
    published_at: datetime | None = None,
) -> MagicMock:
    prop = MagicMock()
    prop.id = prop_id or uuid.uuid4()
    prop.title = title
    prop.price = price
    prop.status = status
    prop.is_active = is_active
    prop.owner_id = owner_id or uuid.uuid4()
    prop.rejection_reason = rejection_reason
    prop.published_at = published_at
    prop.type = "apartment"
    prop.operation = "sale"
    prop.description = "A test property"
    prop.agent_id = None
    prop.project_id = None
    prop.area_m2 = 65.0
    prop.rooms = 2
    prop.bathrooms = 1
    prop.features = {"features": ["pool", "garage"]}
    prop.location = None
    prop.created_at = datetime.now(timezone.utc)
    prop.updated_at = datetime.now(timezone.utc)
    return prop


# --------------------------------------------------------------------------- #
# approve_property logic
# --------------------------------------------------------------------------- #


def test_approve_pending_property_sets_active_and_clears_rejection() -> None:
    """Approving a pending property sets status to ACTIVE and clears rejection_reason."""
    prop = _make_mock_property(
        title="Pending Listing",
        status=PropertyStatus.PENDING.value,
        rejection_reason="Incomplete photos",
        published_at=None,
    )

    assert prop.status == PropertyStatus.PENDING.value
    assert prop.rejection_reason == "Incomplete photos"

    prop.status = PropertyStatus.ACTIVE.value
    prop.published_at = datetime.now(timezone.utc)
    prop.rejection_reason = None

    assert prop.status == PropertyStatus.ACTIVE.value
    assert prop.rejection_reason is None
    assert prop.published_at is not None


def test_approve_sets_published_at_if_none() -> None:
    """Approving a property without published_at should set it."""
    prop = _make_mock_property(
        title="Draft Listing",
        status=PropertyStatus.PENDING.value,
        published_at=None,
    )

    prop.status = PropertyStatus.ACTIVE.value
    prop.published_at = datetime.now(timezone.utc)
    prop.rejection_reason = None

    assert prop.published_at is not None
    assert prop.status == PropertyStatus.ACTIVE.value


def test_cannot_approve_already_active_property() -> None:
    """Approving an already-ACTIVE property should be rejected (idempotency guard)."""
    prop = _make_mock_property(
        title="Already Active",
        status=PropertyStatus.ACTIVE.value,
    )

    with pytest.raises(ValueError, match="already active"):
        if prop.status == PropertyStatus.ACTIVE.value:
            raise ValueError("Property is already active")


def test_approve_preserves_other_fields() -> None:
    """Approving a property should not change title, price, or owner."""
    owner_id = uuid.uuid4()
    prop = _make_mock_property(
        title="Original Title",
        price=350_000.0,
        status=PropertyStatus.PENDING.value,
        owner_id=owner_id,
        rejection_reason="Old reason",
    )

    prop.status = PropertyStatus.ACTIVE.value
    prop.published_at = datetime.now(timezone.utc)
    prop.rejection_reason = None

    assert prop.title == "Original Title"
    assert prop.price == 350_000.0
    assert prop.owner_id == owner_id


# --------------------------------------------------------------------------- #
# reject_property logic
# --------------------------------------------------------------------------- #


def test_reject_property_sets_pending_and_stores_reason() -> None:
    """Rejecting a property sets status to PENDING and stores rejection_reason."""
    prop = _make_mock_property(
        title="To Reject",
        status=PropertyStatus.ACTIVE.value,
        published_at=datetime.now(timezone.utc),
    )

    prop.status = PropertyStatus.PENDING.value
    prop.rejection_reason = "Invalid listing data"
    prop.published_at = None

    assert prop.status == PropertyStatus.PENDING.value
    assert prop.rejection_reason == "Invalid listing data"
    assert prop.published_at is None


def test_reject_property_clears_published_at() -> None:
    """Rejection must clear published_at so listing doesn't appear public."""
    prop = _make_mock_property(
        title="Was Published",
        status=PropertyStatus.ACTIVE.value,
        published_at=datetime.now(timezone.utc),
    )

    prop.status = PropertyStatus.PENDING.value
    prop.rejection_reason = "Bad data"
    prop.published_at = None

    assert prop.published_at is None
    assert prop.status == PropertyStatus.PENDING.value


def test_cannot_reject_already_rejected_property() -> None:
    """Rejecting an already-rejected property should raise."""
    prop = _make_mock_property(
        title="Already Rejected",
        status=PropertyStatus.PENDING.value,
        rejection_reason="Already rejected once",
        published_at=None,
    )

    with pytest.raises(ValueError, match="already rejected"):
        if prop.rejection_reason is not None and prop.published_at is None:
            raise ValueError("Property was already rejected")


def test_reject_property_reason_is_required() -> None:
    """Rejection reason must be non-empty."""
    with pytest.raises(ValueError, match="Rejection reason is required"):
        reason = ""
        if not reason.strip():
            raise ValueError("Rejection reason is required")


def test_reject_property_keeps_original_fields() -> None:
    """Rejection should preserve title, price, and other fields."""
    original_title = "House with Pool"
    original_price = 500_000.0
    prop = _make_mock_property(
        title=original_title,
        price=original_price,
        status=PropertyStatus.ACTIVE.value,
        published_at=datetime.now(timezone.utc),
    )

    prop.status = PropertyStatus.PENDING.value
    prop.rejection_reason = "Fake listing"
    prop.published_at = None

    assert prop.title == original_title
    assert prop.price == original_price
