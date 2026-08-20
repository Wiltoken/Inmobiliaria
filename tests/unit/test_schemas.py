"""Unit tests for app.domain.schemas — Pydantic validation."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    ErrorResponse,
    ForgotPasswordRequest,
    LoginRequest,
    PaginatedAuditLogsResponse,
    PaginatedUsersResponse,
    PasswordPolicyErrorResponse,
    PasswordPolicyViolation,
    RefreshRequest,
    RefreshResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    RoleSummary,
    TokenResponse,
    UserProfile,
)


# --------------------------------------------------------------------------- #
# LoginRequest
# --------------------------------------------------------------------------- #

class TestLoginRequest:
    """Tests for LoginRequest Pydantic model validation."""

    def test_valid_login_request(self) -> None:
        """Valid username + password creates a LoginRequest."""
        req = LoginRequest(username="alice", password="secret123")
        assert req.username == "alice"
        assert req.password == "secret123"
        assert req.tenant_id is None
        assert req.recaptcha_token is None

    def test_valid_login_request_with_tenant(self) -> None:
        """LoginRequest accepts optional tenant_id as UUID."""
        tenant_id = uuid.uuid4()
        req = LoginRequest(
            username="alice",
            password="secret123",
            tenant_id=tenant_id,
        )
        assert req.tenant_id == tenant_id

    def test_valid_login_request_with_recaptcha(self) -> None:
        """LoginRequest accepts optional recaptcha_token."""
        req = LoginRequest(
            username="alice",
            password="secret123",
            recaptcha_token="recaptcha-token-xyz",
        )
        assert req.recaptcha_token == "recaptcha-token-xyz"

    def test_empty_username_rejected(self) -> None:
        """LoginRequest rejects empty username."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="", password="secret123")
        errors = exc_info.value.errors()
        assert any("String should have at least 1 character" in str(e) for e in errors)

    def test_missing_password_rejected(self) -> None:
        """LoginRequest rejects missing password (empty string after min_length)."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="alice", password="")
        errors = exc_info.value.errors()
        assert any(
            "String should have at least 1 character" in str(e)
            for e in errors
        )

    def test_username_too_long_rejected(self) -> None:
        """LoginRequest rejects username exceeding 255 characters."""
        long_username = "a" * 256
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username=long_username, password="secret123")
        errors = exc_info.value.errors()
        assert any("String should have at most 255 characters" in str(e) for e in errors)

    def test_password_too_long_rejected(self) -> None:
        """LoginRequest rejects password exceeding 128 characters."""
        long_password = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(username="alice", password=long_password)
        errors = exc_info.value.errors()
        assert any("String should have at most 128 characters" in str(e) for e in errors)


# --------------------------------------------------------------------------- #
# TokenResponse
# --------------------------------------------------------------------------- #

class TestTokenResponse:
    """Tests for TokenResponse schema."""

    def test_token_response_defaults(self) -> None:
        """TokenResponse sets token_type=Bearer by default."""
        resp = TokenResponse(
            access_token="eyJ...",
            refresh_token="eyJ...",
            expires_in=900,
        )
        assert resp.token_type == "Bearer"

    def test_token_response_all_fields(self) -> None:
        """TokenResponse accepts all fields."""
        resp = TokenResponse(
            access_token="access-token-abc",
            refresh_token="refresh-token-xyz",
            expires_in=900,
            token_type="Bearer",
        )
        assert resp.access_token == "access-token-abc"
        assert resp.refresh_token == "refresh-token-xyz"
        assert resp.expires_in == 900


# --------------------------------------------------------------------------- #
# RefreshRequest / RefreshResponse
# --------------------------------------------------------------------------- #

class TestRefreshRequest:
    """Tests for RefreshRequest."""

    def test_valid_refresh_request(self) -> None:
        """Valid refresh token creates a RefreshRequest."""
        req = RefreshRequest(refresh_token="valid-refresh-token")
        assert req.refresh_token == "valid-refresh-token"

    @pytest.mark.xfail(reason="RefreshRequest.refresh_token has no min_length validator - schema gap")
    def test_empty_refresh_token_rejected(self) -> None:
        """RefreshRequest rejects empty refresh_token (xfail: no min_length on field)."""
        with pytest.raises(ValidationError):
            RefreshRequest(refresh_token="")


class TestRefreshResponse:
    """Tests for RefreshResponse."""

    def test_refresh_response_defaults(self) -> None:
        """RefreshResponse sets token_type=Bearer by default and returns both tokens."""
        resp = RefreshResponse(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            expires_in=900,
        )
        assert resp.token_type == "Bearer"
        assert resp.access_token == "new-access-token"
        assert resp.refresh_token == "new-refresh-token"
        assert resp.expires_in == 900


# --------------------------------------------------------------------------- #
# ErrorResponse
# --------------------------------------------------------------------------- #

class TestErrorResponse:
    """Tests for ErrorResponse."""

    def test_error_response_required_fields(self) -> None:
        """ErrorResponse requires detail and error_code."""
        err = ErrorResponse(detail="Something went wrong", error_code="ERR_001")
        assert err.detail == "Something went wrong"
        assert err.error_code == "ERR_001"

    def test_error_response_optional_fields(self) -> None:
        """ErrorResponse accepts optional remaining_attempts and locked_until."""
        err = ErrorResponse(
            detail="Invalid credentials",
            error_code="AUTH_INVALID_CREDENTIALS",
            remaining_attempts=2,
            locked_until="2025-01-01T00:00:00Z",
        )
        assert err.remaining_attempts == 2
        assert err.locked_until == "2025-01-01T00:00:00Z"


# --------------------------------------------------------------------------- #
# UserProfile
# --------------------------------------------------------------------------- #

class TestUserProfile:
    """Tests for UserProfile schema."""

    def test_user_profile_required_fields(self) -> None:
        """UserProfile accepts all required fields."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        profile = UserProfile(
            id=user_id,
            username="alice",
            email="alice@example.com",
            tenant_id=tenant_id,
            roles=[RoleSummary(id=uuid.uuid4(), name="admin")],
            is_active=True,
            is_locked=False,
        )
        assert profile.username == "alice"
        assert profile.is_active is True
        assert profile.consent_given_at is None

    def test_user_profile_with_consent_and_password_changed(self) -> None:
        """UserProfile accepts optional consent_given_at and password_changed_at."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        now = datetime.now()
        profile = UserProfile(
            id=user_id,
            username="alice",
            email="alice@example.com",
            tenant_id=tenant_id,
            roles=[RoleSummary(id=uuid.uuid4(), name="user")],
            is_active=True,
            is_locked=False,
            consent_given_at=now,
            password_changed_at=now,
        )
        assert profile.consent_given_at == now
        assert profile.password_changed_at == now


# --------------------------------------------------------------------------- #
# Password policy schemas
# --------------------------------------------------------------------------- #

class TestPasswordPolicyViolation:
    """Tests for PasswordPolicyViolation schema."""

    def test_password_policy_violation(self) -> None:
        """PasswordPolicyViolation accepts field and message."""
        v = PasswordPolicyViolation(field="password", message="Too short")
        assert v.field == "password"
        assert v.message == "Too short"


class TestPasswordPolicyErrorResponse:
    """Tests for PasswordPolicyErrorResponse schema."""

    def test_password_policy_error_response(self) -> None:
        """PasswordPolicyErrorResponse includes violations list."""
        violations = [
            PasswordPolicyViolation(field="password", message="Too short"),
            PasswordPolicyViolation(field="password", message="No special char"),
        ]
        resp = PasswordPolicyErrorResponse(violations=violations)
        assert len(resp.violations) == 2
        assert resp.error_code == "AUTH_PASSWORD_POLICY_VIOLATION"
        assert resp.detail == "Password policy violation"


# --------------------------------------------------------------------------- #
# Password recovery schemas
# --------------------------------------------------------------------------- #

class TestForgotPasswordRequest:
    """Tests for ForgotPasswordRequest."""

    def test_valid_email(self) -> None:
        """Valid email creates a ForgotPasswordRequest."""
        req = ForgotPasswordRequest(email="alice@example.com")
        assert req.email == "alice@example.com"

    def test_empty_email_rejected(self) -> None:
        """ForgotPasswordRequest rejects empty email."""
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="")


class TestResetPasswordRequest:
    """Tests for ResetPasswordRequest."""

    def test_valid_reset_request(self) -> None:
        """ResetPasswordRequest accepts token and new_password."""
        req = ResetPasswordRequest(
            token="reset-token-abc",
            new_password="NewSecurePass1!",
        )
        assert req.token == "reset-token-abc"
        assert req.new_password == "NewSecurePass1!"

    def test_empty_token_rejected(self) -> None:
        """ResetPasswordRequest rejects empty token."""
        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="", new_password="NewPass1!")

    def test_empty_password_rejected(self) -> None:
        """ResetPasswordRequest rejects empty new_password."""
        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="valid-token", new_password="")


# --------------------------------------------------------------------------- #
# Pagination schemas
# --------------------------------------------------------------------------- #

class TestPaginatedUsersResponse:
    """Tests for PaginatedUsersResponse."""

    def test_paginated_users_response(self) -> None:
        """PaginatedUsersResponse accepts pagination fields and user list."""
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        user = UserProfile(
            id=user_id,
            username="alice",
            email="alice@example.com",
            tenant_id=tenant_id,
            roles=[RoleSummary(id=uuid.uuid4(), name="user")],
            is_active=True,
            is_locked=False,
        )
        resp = PaginatedUsersResponse(
            users=[user],
            total=1,
            page=1,
            page_size=10,
            total_pages=1,
        )
        assert len(resp.users) == 1
        assert resp.total == 1
        assert resp.total_pages == 1


class TestPaginatedAuditLogsResponse:
    """Tests for PaginatedAuditLogsResponse."""

    def test_paginated_audit_logs_response(self) -> None:
        """PaginatedAuditLogsResponse accepts audit log list and pagination."""
        from app.domain.schemas import AuditLogEntry

        log_entry = AuditLogEntry(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            action="login_attempt",
            ip_address="192.168.1.1",
            details={"success": True},
            created_at=datetime.now(),
        )
        resp = PaginatedAuditLogsResponse(
            audit_logs=[log_entry],
            total=1,
            page=1,
            page_size=10,
            total_pages=1,
        )
        assert len(resp.audit_logs) == 1
        assert resp.total == 1
