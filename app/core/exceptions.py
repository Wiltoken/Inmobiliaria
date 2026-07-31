"""Custom HTTP exceptions with structured error codes per the API contract."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class AuthException(HTTPException):
    """Base auth exception — defaults to 401, overridable via status_code.

    Stores error_code and any extra fields (remaining_attempts, locked_until, etc.)
    so they appear in the JSON response body alongside the detail message.
    """

    def __init__(
        self,
        detail: str,
        error_code: str,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        **extra: Any,
    ) -> None:
        self.error_code = error_code
        # Build a merged detail dict that includes extra fields
        response_body: dict[str, Any] = {"detail": detail, "error_code": error_code}
        response_body.update(extra)
        super().__init__(
            status_code=status_code,
            detail=response_body,
            headers=getattr(self, "headers", None),
        )


class InvalidCredentialsError(AuthException):
    """Wrong username or password."""

    def __init__(self, remaining_attempts: int | None = None) -> None:
        extra: dict[str, object] = {}
        if remaining_attempts is not None:
            extra["remaining_attempts"] = remaining_attempts
        super().__init__(
            detail="Invalid credentials",
            error_code="AUTH_INVALID_CREDENTIALS",
            **extra,
        )


class AccountLockedError(AuthException):
    """Account locked due to too many failed attempts."""

    def __init__(self, locked_until: str | None = None) -> None:
        extra: dict[str, object] = {}
        if locked_until is not None:
            extra["locked_until"] = locked_until
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked",
            error_code="AUTH_ACCOUNT_LOCKED",
            **extra,
        )


class TokenExpiredError(AuthException):
    """JWT has expired."""

    def __init__(self) -> None:
        super().__init__(
            detail="Token has expired",
            error_code="AUTH_TOKEN_EXPIRED",
        )


class TokenRevokedError(AuthException):
    """JWT has been revoked (blacklisted or logout)."""

    def __init__(self) -> None:
        super().__init__(
            detail="Token has been revoked",
            error_code="AUTH_TOKEN_REVOKED",
        )


class InvalidTokenError(AuthException):
    """Malformed or invalid JWT."""

    def __init__(self) -> None:
        super().__init__(
            detail="Invalid token",
            error_code="AUTH_TOKEN_INVALID",
        )


class InsufficientRoleError(HTTPException):
    """User lacks required role for endpoint."""

    def __init__(self, required_roles: list[str]) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
        self.error_code = "AUTH_INSUFFICIENT_ROLE"
        self.required_roles = required_roles


class PasswordExpiredError(AuthException):
    """User's password has expired and must be changed."""

    def __init__(self) -> None:
        super().__init__(
            detail="Password has expired",
            error_code="AUTH_PASSWORD_EXPIRED",
        )


class PasswordPolicyError(HTTPException):
    """Password does not meet policy requirements."""

    def __init__(self, violations: list[dict[str, str]]) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password policy violation",
        )
        self.error_code = "AUTH_PASSWORD_POLICY_VIOLATION"
        self.violations = violations


class CaptchaFailedError(AuthException):
    """reCAPTCHA verification failed or score below threshold."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAPTCHA verification failed",
            error_code="AUTH_CAPTCHA_FAILED",
        )


class SessionExpiredError(AuthException):
    """User session has expired due to inactivity."""

    def __init__(self) -> None:
        super().__init__(
            detail="Session has expired due to inactivity",
            error_code="AUTH_SESSION_EXPIRED",
        )
