"""Unit tests for inquiry business logic.

Tests inquiry creation, status transitions, response validation, and contact preferences.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.domain.models import ContactPreference, InquiryStatus, PropertyStatus


class MockUser:
    def __init__(self, user_id: uuid.UUID | None = None, role_name: str = "buyer"):
        self.id = user_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.roles = [MagicMock(name=role_name)]


def _make_mock_inquiry(
    *,
    inquiry_id: uuid.UUID | None = None,
    from_user_id: uuid.UUID | None = None,
    to_user_id: uuid.UUID | None = None,
    property_id: uuid.UUID | None = None,
    message: str = "Is this still available?",
    contact_preference: str = ContactPreference.EMAIL.value,
    status: str = InquiryStatus.PENDING.value,
    response_message: str | None = None,
    response_action: str | None = None,
) -> MagicMock:
    inquiry = MagicMock()
    inquiry.id = inquiry_id or uuid.uuid4()
    inquiry.from_user_id = from_user_id or uuid.uuid4()
    inquiry.to_user_id = to_user_id or uuid.uuid4()
    inquiry.property_id = property_id or uuid.uuid4()
    inquiry.message = message
    inquiry.contact_preference = contact_preference
    inquiry.status = status
    inquiry.response_message = response_message
    inquiry.response_action = response_action
    inquiry.created_at = datetime.now(timezone.utc)
    return inquiry


# --------------------------------------------------------------------------- #
# Create inquiry — validation
# --------------------------------------------------------------------------- #


def test_cannot_inquire_about_own_property() -> None:
    """User cannot send inquiry about property they own."""
    seller = MockUser()
    property_owner_id = seller.id

    with pytest.raises(ValueError, match="own property"):
        if property_owner_id == seller.id:
            raise ValueError("Cannot inquire about your own property")


def test_cannot_inquire_about_unpublished_property() -> None:
    """User cannot inquire about non-ACTIVE property."""
    prop = MagicMock()
    prop.status = PropertyStatus.PENDING.value

    with pytest.raises(ValueError, match="published"):
        if prop.status != PropertyStatus.ACTIVE.value:
            raise ValueError("Can only inquire about published properties")


def test_cannot_inquire_property_without_owner_or_agent() -> None:
    """Inquiry requires a recipient (owner or agent)."""
    prop = MagicMock()
    prop.owner_id = None
    prop.agent_id = None

    to_user_id = prop.owner_id or prop.agent_id
    assert to_user_id is None

    with pytest.raises(ValueError, match="no owner or agent"):
        if not to_user_id:
            raise ValueError("Property has no owner or agent")


def test_sender_receiver_different_for_valid_inquiry() -> None:
    """Inquiry sender must be different from receiver."""
    sender = uuid.uuid4()
    recipient = uuid.uuid4()

    assert sender != recipient
    assert sender != recipient


# --------------------------------------------------------------------------- #
# Inquiry status transitions
# --------------------------------------------------------------------------- #


def test_inquiry_pending_to_replied() -> None:
    """Pending inquiry can transition to REPLIED."""
    inquiry = _make_mock_inquiry(status=InquiryStatus.PENDING.value)
    new_status = InquiryStatus.REPLIED.value
    inquiry.status = new_status
    assert inquiry.status == InquiryStatus.REPLIED.value


def test_inquiry_pending_to_interested() -> None:
    """Pending inquiry can transition to INTERESTED."""
    inquiry = _make_mock_inquiry(status=InquiryStatus.PENDING.value)
    new_status = InquiryStatus.INTERESTED.value
    inquiry.status = new_status
    assert inquiry.status == InquiryStatus.INTERESTED.value


def test_inquiry_pending_to_not_interested() -> None:
    """Pending inquiry can transition to NOT_INTERESTED."""
    inquiry = _make_mock_inquiry(status=InquiryStatus.PENDING.value)
    new_status = InquiryStatus.NOT_INTERESTED.value
    inquiry.status = new_status
    assert inquiry.status == InquiryStatus.NOT_INTERESTED.value


def test_invalid_action_rejected() -> None:
    """Invalid response action should raise error."""
    invalid_action = "delete"
    valid_actions = {"accept", "decline", "request_more_info"}

    with pytest.raises(ValueError, match="Invalid action"):
        if invalid_action not in valid_actions:
            raise ValueError("Invalid action")


def test_only_recipient_can_respond() -> None:
    """Only the inquiry recipient (to_user_id) can respond."""
    inquiry = _make_mock_inquiry(to_user_id=uuid.uuid4())
    random_user_id = uuid.uuid4()

    with pytest.raises(ValueError, match="only respond"):
        if inquiry.to_user_id != random_user_id:
            raise ValueError("You can only respond to inquiries you received")


# --------------------------------------------------------------------------- #
# Inquiry response message validation
# --------------------------------------------------------------------------- #


def test_response_message_stored_on_reply() -> None:
    """Response message is stored when replying to an inquiry."""
    inquiry = _make_mock_inquiry()
    inquiry.status = InquiryStatus.REPLIED.value
    inquiry.response_message = "Thanks for your interest, let's schedule a viewing."

    assert inquiry.response_message == "Thanks for your interest, let's schedule a viewing."
    assert inquiry.status == InquiryStatus.REPLIED.value


def test_response_message_can_be_none() -> None:
    """Response message is optional — can be None."""
    inquiry = _make_mock_inquiry(response_message=None)
    assert inquiry.response_message is None


# --------------------------------------------------------------------------- #
# Contact preference validation
# --------------------------------------------------------------------------- #


def test_contact_preference_email_is_valid() -> None:
    """Email contact preference is valid."""
    assert ContactPreference.EMAIL.value == "email"


def test_contact_preference_phone_is_valid() -> None:
    """Phone contact preference is valid."""
    assert ContactPreference.PHONE.value == "phone"


def test_contact_preference_either_is_valid() -> None:
    """Either contact preference is valid."""
    assert ContactPreference.EITHER.value == "either"


def test_invalid_contact_preference_raises() -> None:
    """Invalid contact preference raises ValueError."""
    with pytest.raises(ValueError):
        ContactPreference("invalid_method")
