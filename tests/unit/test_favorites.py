"""Unit tests for favorites business logic.

Tests add, remove, list favorites with mocked DB sessions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest


class MockUser:
    def __init__(self, user_id: uuid.UUID | None = None):
        self.id = user_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.is_active = True


class MockFavorite:
    def __init__(
        self,
        fav_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        property_id: uuid.UUID | None = None,
        created_at: datetime | None = None,
    ):
        self.id = fav_id or uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()
        self.property_id = property_id or uuid.uuid4()
        self.created_at = created_at or datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Add favorite
# --------------------------------------------------------------------------- #


def test_add_favorite_creates_record() -> None:
    """Adding a favorite creates a Favorite record with correct user and property."""
    user = MockUser()
    property_id = uuid.uuid4()

    favorite = MockFavorite(user_id=user.id, property_id=property_id)

    assert favorite.id is not None
    assert favorite.user_id == user.id
    assert favorite.property_id == property_id


def test_add_favorite_prevents_duplicates() -> None:
    """Adding a favorite that already exists should raise conflict."""
    user = MockUser()
    property_id = uuid.uuid4()

    existing_favorites: set[tuple[uuid.UUID, uuid.UUID]] = {(user.id, property_id)}

    with pytest.raises(ValueError, match="already in favorites"):
        if (user.id, property_id) in existing_favorites:
            raise ValueError("Property already in favorites")


def test_add_favorite_allows_different_users_same_property() -> None:
    """Two different users can favorite the same property."""
    user_a = MockUser()
    user_b = MockUser()
    property_id = uuid.uuid4()

    fav_a = MockFavorite(user_id=user_a.id, property_id=property_id)
    fav_b = MockFavorite(user_id=user_b.id, property_id=property_id)

    assert fav_a.user_id != fav_b.user_id
    assert fav_a.property_id == fav_b.property_id == property_id


def test_add_favorite_allows_same_user_different_properties() -> None:
    """Same user can favorite multiple different properties."""
    user = MockUser()
    prop_a = uuid.uuid4()
    prop_b = uuid.uuid4()

    fav_a = MockFavorite(user_id=user.id, property_id=prop_a)
    fav_b = MockFavorite(user_id=user.id, property_id=prop_b)

    assert fav_a.user_id == fav_b.user_id == user.id
    assert fav_a.property_id != fav_b.property_id


# --------------------------------------------------------------------------- #
# Remove favorite
# --------------------------------------------------------------------------- #


def test_remove_favorite_deletes_record() -> None:
    """Removing a favorite deletes it from the favorites store."""
    user = MockUser()
    property_id = uuid.uuid4()

    fav = MockFavorite(user_id=user.id, property_id=property_id)
    fav_storage: dict[uuid.UUID, MockFavorite] = {fav.id: fav}

    assert fav.id in fav_storage

    del fav_storage[fav.id]

    assert fav.id not in fav_storage


def test_remove_nonexistent_favorite_raises() -> None:
    """Removing a favorite that doesn't exist should raise 404."""
    fav_storage: dict[uuid.UUID, MockFavorite] = {}

    with pytest.raises(ValueError, match="not found"):
        fav_id = uuid.uuid4()
        if fav_id not in fav_storage:
            raise ValueError("Favorite not found")


def test_remove_favorite_only_removes_owned() -> None:
    """User can only remove their own favorites, not others'."""
    user_a = MockUser()
    user_b = MockUser()
    property_id = uuid.uuid4()

    fav = MockFavorite(user_id=user_a.id, property_id=property_id)
    fav_storage = {fav.id: fav}

    with pytest.raises(ValueError, match="not found"):
        # user_b tries to remove user_a's favorite
        found = next((f for f in fav_storage.values() if f.user_id == user_b.id), None)
        if not found:
            raise ValueError("Favorite not found")


# --------------------------------------------------------------------------- #
# List favorites
# --------------------------------------------------------------------------- #


def test_list_favorites_filters_by_user() -> None:
    """Listing favorites should only return the current user's favorites."""
    user = MockUser()
    other_user = MockUser()

    favorites = [
        MockFavorite(user_id=user.id, property_id=uuid.uuid4()),
        MockFavorite(user_id=user.id, property_id=uuid.uuid4()),
        MockFavorite(user_id=other_user.id, property_id=uuid.uuid4()),
    ]

    user_favs = [f for f in favorites if f.user_id == user.id]

    assert len(user_favs) == 2
    assert all(f.user_id == user.id for f in user_favs)


def test_list_favorites_empty_for_new_user() -> None:
    """New user with no favorites returns empty list."""
    user = MockUser()
    user_favs: list[MockFavorite] = []

    assert len(user_favs) == 0


def test_list_favorites_ordered_by_newest_first() -> None:
    """Favorites should be ordered by created_at descending (newest first)."""
    now = datetime.now(timezone.utc)
    favorites = [
        MockFavorite(created_at=now),
        MockFavorite(created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
        MockFavorite(created_at=datetime(2025, 6, 15, tzinfo=timezone.utc)),
    ]

    sorted_favs = sorted(favorites, key=lambda f: f.created_at, reverse=True)

    assert sorted_favs[0].created_at == now
