"""Query helpers for common SQLAlchemy patterns."""

from __future__ import annotations

from sqlalchemy import Select


def exclude_deleted(query: Select, model: type) -> Select:
    """Add WHERE clause to exclude soft-deleted records."""
    if hasattr(model, "is_deleted"):
        return query.where(model.is_deleted == False)
    if hasattr(model, "deleted_at"):
        return query.where(model.deleted_at.is_(None))
    return query
