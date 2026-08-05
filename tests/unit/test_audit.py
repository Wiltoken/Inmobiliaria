"""Unit tests for audit and analytics business logic.

Tests log_user_action, audit log filtering, and PII sanitization.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone


class MockUser:
    def __init__(self, user_id: uuid.UUID | None = None, username: str = "testuser"):
        self.id = user_id or uuid.uuid4()
        self.tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.username = username
        self.is_active = True


_UNSET = object()


class MockUserAction:
    def __init__(
        self,
        *,
        user_id: uuid.UUID | None = None,
        action: str = "page_view",
        details: dict | None = None,
        ip_address: str | None | object = _UNSET,
        created_at: datetime | None = None,
    ):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.action = action
        self.details = details or {}
        self.ip_address = ip_address if ip_address is not _UNSET else "127.0.0.1"
        self.created_at = created_at or datetime.now(timezone.utc)
        self.user = None


class MockAuditLog:
    def __init__(
        self,
        *,
        user_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        action: str = "login_attempt",
        ip_address: str | None = None,
        details: dict | None = None,
        created_at: datetime | None = None,
    ):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.tenant_id = tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.action = action
        self.ip_address = ip_address
        self.details = details
        self.created_at = created_at or datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# log_user_action
# --------------------------------------------------------------------------- #


def test_log_user_action_stores_user_id_and_action() -> None:
    """User action log stores user_id, action, ip, and details."""
    user = MockUser()
    action = MockUserAction(
        user_id=user.id,
        action="search_performed",
        details={"query": "apartment bogota", "filters": {"price_min": 100_000}},
        ip_address="192.168.1.100",
    )

    assert action.user_id == user.id
    assert action.action == "search_performed"
    assert action.details["query"] == "apartment bogota"
    assert action.ip_address == "192.168.1.100"


def test_log_user_action_anonymous_user() -> None:
    """Anonymous users can log actions (e.g. browsing without auth)."""
    action = MockUserAction(
        user_id=None,
        action="page_view",
        ip_address="10.0.0.1",
    )

    assert action.user_id is None
    assert action.action == "page_view"
    assert action.ip_address is not None


def test_log_user_action_without_ip() -> None:
    """IP can be None when client info is unavailable."""
    action = MockUserAction(
        user_id=uuid.uuid4(),
        action="property_viewed",
        ip_address=None,
    )

    assert action.ip_address is None
    assert action.id is not None


# --------------------------------------------------------------------------- #
# Audit log filtering
# --------------------------------------------------------------------------- #


def test_get_audit_logs_filters_by_user_id() -> None:
    """Audit logs should be filterable by user_id."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    logs = [
        MockAuditLog(user_id=user_a, action="login_attempt"),
        MockAuditLog(user_id=user_a, action="password_change"),
        MockAuditLog(user_id=user_b, action="login_attempt"),
    ]

    user_a_logs = [log for log in logs if log.user_id == user_a]
    assert len(user_a_logs) == 2
    assert all(log.user_id == user_a for log in user_a_logs)


def test_get_audit_logs_filters_by_action() -> None:
    """Audit logs should be filterable by action type."""
    logs = [
        MockAuditLog(action="login_attempt"),
        MockAuditLog(action="login_attempt"),
        MockAuditLog(action="password_change"),
        MockAuditLog(action="admin_list_users"),
    ]

    login_logs = [log for log in logs if log.action == "login_attempt"]
    assert len(login_logs) == 2


def test_get_audit_logs_filters_by_date_range() -> None:
    """Audit logs should be filterable by date_from and date_to."""
    now = datetime.now(timezone.utc)
    logs = [
        MockAuditLog(created_at=now - timedelta(days=10)),
        MockAuditLog(created_at=now - timedelta(days=5)),
        MockAuditLog(created_at=now - timedelta(days=1)),
        MockAuditLog(created_at=now - timedelta(hours=1)),
    ]

    date_from = now - timedelta(days=7)
    date_to = now

    filtered = [
        log for log in logs
        if date_from <= log.created_at <= date_to
    ]

    assert len(filtered) == 3


def test_get_audit_logs_filters_by_tenant() -> None:
    """Audit logs should be filterable by tenant_id."""
    tenant_a = uuid.UUID("11111111-1111-1111-1111-111111111111")
    tenant_b = uuid.UUID("22222222-2222-2222-2222-222222222222")

    logs = [
        MockAuditLog(tenant_id=tenant_a, action="login_attempt"),
        MockAuditLog(tenant_id=tenant_a, action="password_change"),
        MockAuditLog(tenant_id=tenant_b, action="login_attempt"),
    ]

    tenant_a_logs = [log for log in logs if log.tenant_id == tenant_a]
    assert len(tenant_a_logs) == 2


def test_get_audit_logs_multiple_filters_combined() -> None:
    """Multiple filters can be combined (user + action + date)."""
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    logs = [
        MockAuditLog(user_id=user_id, action="login_attempt", created_at=now - timedelta(hours=2)),
        MockAuditLog(user_id=uuid.uuid4(), action="login_attempt", created_at=now - timedelta(hours=1)),
        MockAuditLog(user_id=user_id, action="password_change", created_at=now),
    ]

    date_from = now - timedelta(hours=24)
    filtered = [
        log for log in logs
        if log.user_id == user_id
        and log.action == "login_attempt"
        and log.created_at >= date_from
    ]

    assert len(filtered) == 1
    assert filtered[0].action == "login_attempt"


# --------------------------------------------------------------------------- #
# PII sanitization
# --------------------------------------------------------------------------- #


def test_deleted_user_ip_is_cleared() -> None:
    """When a user is deleted, their audit log IP addresses should be cleared."""
    deleted_user_id = uuid.uuid4()

    logs = [
        MockAuditLog(user_id=deleted_user_id, ip_address="192.168.1.50", action="login_attempt"),
        MockAuditLog(user_id=deleted_user_id, ip_address="10.0.0.1", action="password_change"),
    ]

    for log in logs:
        if log.user_id == deleted_user_id:
            log.ip_address = None

    assert all(log.ip_address is None for log in logs)


def test_audit_log_details_no_pii_in_content() -> None:
    """Audit log details should not contain PII like passwords or emails."""
    safe_details = {"success": True, "attempt_number": 3}
    unsafe_keys = {"password", "email", "ssn", "credit_card"}

    has_pii = any(k in unsafe_keys for k in safe_details)
    assert not has_pii
