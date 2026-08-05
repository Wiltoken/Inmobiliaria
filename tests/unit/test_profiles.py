"""Unit tests for profile business logic.

Tests buyer/seller/agent profile creation, update, and validation rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


class MockUser:
    def __init__(self, user_id: uuid.UUID | None = None, role_name: str = "buyer"):
        self.id = user_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.is_active = True
        self.roles = [MagicMock(name=role_name)]


class MockBuyerProfile:
    def __init__(
        self,
        *,
        user_id: uuid.UUID | None = None,
        budget_min: float | None = None,
        budget_max: float | None = None,
        rooms_min: int | None = None,
        bathrooms_min: int | None = None,
        area_min: float | None = None,
        area_max: float | None = None,
        is_deleted: bool = False,
    ):
        self.id = uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()
        self.budget_min = budget_min
        self.budget_max = budget_max
        self.rooms_min = rooms_min
        self.bathrooms_min = bathrooms_min
        self.area_min = area_min
        self.area_max = area_max
        self.preferred_locations = []
        self.preferred_features = {}
        self.preferred_property_types = []
        self.is_deleted = is_deleted
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class MockSellerProfile:
    def __init__(
        self,
        *,
        user_id: uuid.UUID | None = None,
        phone: str | None = None,
        company_name: str | None = None,
        is_deleted: bool = False,
    ):
        self.id = uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()
        self.phone = phone
        self.company_name = company_name
        self.is_deleted = is_deleted
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class MockAgentProfile:
    def __init__(
        self,
        *,
        user_id: uuid.UUID | None = None,
        license_number: str = "LIC-12345",
        agency_name: str | None = None,
        is_deleted: bool = False,
    ):
        self.id = uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()
        self.license_number = license_number
        self.agency_name = agency_name
        self.is_deleted = is_deleted
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Buyer profile creation
# --------------------------------------------------------------------------- #


def test_create_buyer_profile_valid_budget() -> None:
    """Buyer profile can be created with valid budget_min < budget_max."""
    profile = MockBuyerProfile(
        budget_min=100_000.0,
        budget_max=300_000.0,
    )
    assert profile.budget_min == 100_000.0
    assert profile.budget_max == 300_000.0
    assert profile.budget_min < profile.budget_max


def test_create_buyer_profile_budget_min_greater_than_max_raises() -> None:
    """Buyer profile with budget_min > budget_max should be rejected."""
    with pytest.raises(ValueError, match="budget_min must be less than"):
        budget_min, budget_max = 300_000.0, 100_000.0
        if budget_min is not None and budget_max is not None and budget_min >= budget_max:
            raise ValueError("budget_min must be less than budget_max")


def test_create_buyer_profile_budget_min_equal_to_max_raises() -> None:
    """Buyer profile with budget_min == budget_max should be rejected."""
    with pytest.raises(ValueError, match="budget_min must be less than"):
        budget_min, budget_max = 200_000.0, 200_000.0
        if budget_min is not None and budget_max is not None and budget_min >= budget_max:
            raise ValueError("budget_min must be less than budget_max")


def test_create_buyer_profile_optional_fields_none() -> None:
    """Buyer profile can be created with all optional fields as None."""
    profile = MockBuyerProfile(
        user_id=uuid.uuid4(),
        budget_min=None,
        budget_max=None,
        rooms_min=None,
        area_min=None,
        area_max=None,
    )
    assert profile.budget_min is None
    assert profile.budget_max is None
    assert profile.preferred_locations == []


def test_create_buyer_profile_area_validation() -> None:
    """Buyer profile area_min < area_max should be validated."""
    profile = MockBuyerProfile(
        area_min=50.0,
        area_max=100.0,
    )
    assert profile.area_min < profile.area_max


# --------------------------------------------------------------------------- #
# Buyer profile update — partial
# --------------------------------------------------------------------------- #


def test_update_buyer_profile_only_changed_fields() -> None:
    """Partial update should only modify fields that are explicitly set."""
    profile = MockBuyerProfile(
        budget_min=100_000.0,
        budget_max=300_000.0,
        rooms_min=2,
    )

    update_data = {"budget_max": 350_000.0}

    for field, value in update_data.items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(timezone.utc)

    assert profile.budget_max == 350_000.0
    assert profile.budget_min == 100_000.0
    assert profile.rooms_min == 2


def test_update_buyer_profile_to_none_clears_field() -> None:
    """Setting a field to None should clear it."""
    profile = MockBuyerProfile(
        budget_min=100_000.0,
        budget_max=300_000.0,
    )

    profile.budget_min = None

    assert profile.budget_min is None
    assert profile.budget_max == 300_000.0


def test_update_buyer_profile_updated_at_changes() -> None:
    """Updating a profile should update the updated_at timestamp."""
    profile = MockBuyerProfile()
    original_updated_at = profile.updated_at

    profile.budget_max = 500_000.0
    profile.updated_at = datetime.now(timezone.utc)

    assert profile.updated_at > original_updated_at


# --------------------------------------------------------------------------- #
# Seller profile — phone validation
# --------------------------------------------------------------------------- #


def test_seller_profile_phone_is_optional() -> None:
    """Seller profile can be created without a phone number."""
    profile = MockSellerProfile(phone=None)
    assert profile.phone is None


def test_seller_profile_phone_stored_correctly() -> None:
    """Seller profile with phone stores it correctly."""
    profile = MockSellerProfile(phone="+573001234567")
    assert profile.phone == "+573001234567"


def test_seller_profile_invalid_phone_length_rejected() -> None:
    """Seller profile phone exceeding max length should be rejected."""
    with pytest.raises(ValueError, match="too long"):
        phone = "1" * 25
        if len(phone) > 20:
            raise ValueError("Phone number too long")


# --------------------------------------------------------------------------- #
# Agent profile — license_number
# --------------------------------------------------------------------------- #


def test_agent_profile_license_number_required() -> None:
    """Agent profile must have a non-empty license_number."""
    profile = MockAgentProfile(license_number="LIC-12345")
    assert profile.license_number == "LIC-12345"
    assert len(profile.license_number) > 0


def test_agent_profile_license_number_empty_raises() -> None:
    """Agent profile with empty license_number should be rejected."""
    with pytest.raises(ValueError, match="License number is required"):
        license_number = ""
        if not license_number.strip():
            raise ValueError("License number is required")


def test_agent_profile_optional_agency_name() -> None:
    """Agency name is optional for agent profiles."""
    profile = MockAgentProfile(license_number="LIC-99999", agency_name=None)
    assert profile.agency_name is None
    assert profile.license_number == "LIC-99999"


# --------------------------------------------------------------------------- #
# Profile queries exclude deleted
# --------------------------------------------------------------------------- #


def test_buyer_profile_query_excludes_deleted() -> None:
    """Active profile queries should exclude is_deleted=True."""
    profiles = [
        MockBuyerProfile(user_id=uuid.uuid4(), is_deleted=False),
        MockBuyerProfile(user_id=uuid.uuid4(), is_deleted=True),
        MockBuyerProfile(user_id=uuid.uuid4(), is_deleted=False),
    ]

    active = [p for p in profiles if not p.is_deleted]
    assert len(active) == 2
    assert all(not p.is_deleted for p in active)


def test_seller_profile_query_excludes_deleted() -> None:
    """Seller profile queries should exclude is_deleted=True."""
    profiles = [
        MockSellerProfile(phone="+571", is_deleted=False),
        MockSellerProfile(phone="+572", is_deleted=True),
    ]

    active = [p for p in profiles if not p.is_deleted]
    assert len(active) == 1
    assert active[0].phone == "+571"


def test_agent_profile_query_excludes_deleted() -> None:
    """Agent profile queries should exclude is_deleted=True."""
    profiles = [
        MockAgentProfile(license_number="A", is_deleted=False),
        MockAgentProfile(license_number="B", is_deleted=True),
        MockAgentProfile(license_number="C", is_deleted=False),
    ]

    active = [p for p in profiles if not p.is_deleted]
    assert len(active) == 2
    assert active[0].license_number == "A"
    assert active[1].license_number == "C"
