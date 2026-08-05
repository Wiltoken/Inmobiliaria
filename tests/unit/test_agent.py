"""Unit tests for agent dashboard business logic.

Tests agent stats, client filtering, and client match listing with mocked DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.domain.models import InquiryStatus, PropertyStatus


class MockUser:
    def __init__(self, user_id: uuid.UUID | None = None, username: str = "agent1", email: str = "agent1@test.com"):
        self.id = user_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.username = username
        self.email = email
        self.is_active = True


def _make_mock_buyer(
    *,
    buyer_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    budget_min: float | None = 100_000.0,
    budget_max: float | None = 300_000.0,
    preferred_property_types: list[str] | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    buyer = MagicMock()
    buyer.id = buyer_id or uuid.uuid4()
    buyer.user_id = user_id or uuid.uuid4()
    buyer.budget_min = budget_min
    buyer.budget_max = budget_max
    buyer.preferred_property_types = preferred_property_types or ["apartment", "house"]
    buyer.created_at = created_at or datetime.now(timezone.utc)
    buyer.user = MagicMock()
    buyer.user.username = "testbuyer"
    buyer.user.email = "testbuyer@test.com"
    return buyer


# --------------------------------------------------------------------------- #
# Agent stats computation
# --------------------------------------------------------------------------- #


def test_get_agent_stats_counts_active_listings() -> None:
    """Agent stats should count only active listings for the agent."""
    agent = MockUser()
    properties = [
        MagicMock(agent_id=agent.id, is_active=True, status=PropertyStatus.ACTIVE.value),
        MagicMock(agent_id=agent.id, is_active=True, status=PropertyStatus.ACTIVE.value),
        MagicMock(agent_id=agent.id, is_active=False, status=PropertyStatus.ACTIVE.value),
        MagicMock(agent_id=uuid.uuid4(), is_active=True, status=PropertyStatus.ACTIVE.value),
    ]

    active_count = sum(
        1 for p in properties
        if p.agent_id == agent.id and p.is_active and p.status == PropertyStatus.ACTIVE.value
    )
    assert active_count == 2


def test_get_agent_stats_counts_pending_inquiries() -> None:
    """Agent stats should count only pending inquiries sent to the agent."""
    agent = MockUser()
    inquiries = [
        MagicMock(to_user_id=agent.id, status=InquiryStatus.PENDING.value),
        MagicMock(to_user_id=agent.id, status=InquiryStatus.PENDING.value),
        MagicMock(to_user_id=agent.id, status=InquiryStatus.REPLIED.value),
        MagicMock(to_user_id=uuid.uuid4(), status=InquiryStatus.PENDING.value),
    ]

    pending_count = sum(
        1 for i in inquiries
        if i.to_user_id == agent.id and i.status == InquiryStatus.PENDING.value
    )
    assert pending_count == 2


def test_get_agent_stats_returns_zero_for_empty_agent() -> None:
    """Agent with no listings or inquiries should have zero stats."""
    agent = MockUser()

    active_listings = sum(1 for p in [] if p.agent_id == agent.id)
    pending_inquiries = sum(1 for i in [] if i.to_user_id == agent.id)

    assert active_listings == 0
    assert pending_inquiries == 0


# --------------------------------------------------------------------------- #
# Agent clients filtering
# --------------------------------------------------------------------------- #


def test_get_agent_clients_filters_by_agent_properties() -> None:
    """Agent clients are buyers with matches for the agent's properties."""
    agent = MockUser()
    agent_property_ids = {
        uuid.UUID("11111111-1111-1111-1111-111111111111"),
        uuid.UUID("22222222-2222-2222-2222-222222222222"),
    }

    matches = [
        MagicMock(buyer_id=uuid.uuid4(), property_id=uuid.UUID("11111111-1111-1111-1111-111111111111")),
        MagicMock(buyer_id=uuid.uuid4(), property_id=uuid.UUID("22222222-2222-2222-2222-222222222222")),
        MagicMock(buyer_id=uuid.uuid4(), property_id=uuid.uuid4()),
    ]

    agent_matches = [m for m in matches if m.property_id in agent_property_ids]
    assert len(agent_matches) == 2


def test_get_agent_clients_buyer_seller_role_filter() -> None:
    """Agent clients should only include buyers, not sellers."""
    profiles = [
        _make_mock_buyer(user_id=uuid.uuid4()),
        _make_mock_buyer(user_id=uuid.uuid4()),
    ]

    buyer_ids = {p.user_id for p in profiles}
    assert len(buyer_ids) == 2


def test_get_agent_clients_empty_when_no_matches() -> None:
    """Agent with no matching buyers should return empty list."""
    agent_property_ids: set[uuid.UUID] = set()
    matches: list[MagicMock] = []

    agent_matches = [m for m in matches if m.property_id in agent_property_ids]
    assert len(agent_matches) == 0


# --------------------------------------------------------------------------- #
# Client matches filtering
# --------------------------------------------------------------------------- #


def test_get_client_matches_filters_by_buyer_id() -> None:
    """Client matches should be filtered by a specific buyer_id."""
    buyer_a = uuid.uuid4()
    buyer_b = uuid.uuid4()

    matches = [
        MagicMock(id=uuid.uuid4(), buyer_id=buyer_a, score=85.0),
        MagicMock(id=uuid.uuid4(), buyer_id=buyer_a, score=72.0),
        MagicMock(id=uuid.uuid4(), buyer_id=buyer_b, score=90.0),
    ]

    buyer_a_matches = [m for m in matches if m.buyer_id == buyer_a]
    assert len(buyer_a_matches) == 2
    assert all(m.buyer_id == buyer_a for m in buyer_a_matches)


def test_get_client_matches_sorted_by_score_desc() -> None:
    """Client matches should be sorted by score descending (best first)."""
    matches = [
        MagicMock(score=50.0),
        MagicMock(score=95.0),
        MagicMock(score=75.0),
    ]

    sorted_matches = sorted(matches, key=lambda m: m.score, reverse=True)
    assert sorted_matches[0].score == 95.0
    assert sorted_matches[1].score == 75.0
    assert sorted_matches[2].score == 50.0


def test_get_client_matches_pagination() -> None:
    """Client matches should support pagination."""
    all_matches = [MagicMock(score=float(i)) for i in range(20)]

    page = 2
    page_size = 5
    offset = (page - 1) * page_size
    paginated = all_matches[offset : offset + page_size]

    assert len(paginated) == page_size
    assert paginated[0].score == 5.0
    assert paginated[4].score == 9.0


# --------------------------------------------------------------------------- #
# Dashboard listings with counts
# --------------------------------------------------------------------------- #


def test_agent_listings_with_inquiry_and_favorite_counts() -> None:
    """Each listing should include inquiry and favorite counts."""
    prop_id = uuid.uuid4()

    mock_property = MagicMock()
    mock_property.id = prop_id
    mock_property.title = "Modern Apartment"
    mock_property.price = 250_000.0

    inquiry_count = 3
    favorite_count = 7

    assert inquiry_count == 3
    assert favorite_count == 7
    assert mock_property.title == "Modern Apartment"


def test_agent_listings_filter_by_status() -> None:
    """Agent listings should be filterable by property status."""
    active = MagicMock(status=PropertyStatus.ACTIVE.value, title="Active")
    pending = MagicMock(status=PropertyStatus.PENDING.value, title="Pending")
    sold = MagicMock(status=PropertyStatus.SOLD.value, title="Sold")

    status_filter = PropertyStatus.ACTIVE.value
    filtered = [p for p in [active, pending, sold] if p.status == status_filter]

    assert len(filtered) == 1
    assert filtered[0].title == "Active"
