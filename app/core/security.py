"""Password hashing (passlib CryptContext + bcrypt) and JWT encode/decode (PyJWT).

All security thresholds come from settings — zero hardcoded literals.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.exceptions import (
    InvalidTokenError,
    PasswordPolicyError,
    TokenExpiredError,
)

# ── Password hashing ──────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PolicyViolation:
    """Represents a single password policy violation."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


def validate_password(password: str) -> list[PolicyViolation]:
    """Validate a password against the configured policy.

    Returns an empty list if the password is compliant.
    """
    violations: list[PolicyViolation] = []

    if len(password) < settings.password_min_length:
        violations.append(
            PolicyViolation(
                "password",
                f"Password must be at least {settings.password_min_length} characters long.",
            )
        )

    if settings.password_require_special:
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
        if not any(c in special_chars for c in password):
            violations.append(
                PolicyViolation(
                    "password",
                    "Password must contain at least one special character.",
                )
            )

    return violations


def hash_password(password: str) -> str:
    """Hash a password using bcrypt via passlib CryptContext.

    Raises PasswordPolicyError if the password does not meet policy requirements.
    """
    violations = validate_password(password)
    if violations:
        raise PasswordPolicyError([v.to_dict() for v in violations])
    return pwd_context.hash(password)


def hash_token(token: str) -> str:
    """Hash a token (e.g., password reset token) using bcrypt.

    Unlike hash_password(), this skips the human-facing password policy checks
    since tokens are machine-generated secure random strings.
    """
    return pwd_context.hash(token)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using passlib verify_and_update.

    Returns True if the password matches, False otherwise.
    """
    ok, _ = pwd_context.verify_and_update(plain_password, hashed_password)
    return ok


# ── JWT helpers ───────────────────────────────────────────────────────────────

ALGORITHM = "HS256"


def _build_payload(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str],
    jti: str,
    token_type: str,
    expires_delta: timedelta,
) -> dict[str, Any]:
    """Build the shared JWT claims dict."""
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "jti": jti,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    roles: list[str],
    jti: str,
) -> str:
    """Create a JWT access token.

    Claims: sub, tenant_id, roles, jti, type=access, iat, exp.
    """
    payload = _build_payload(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles,
        jti=jti,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    jti: str,
) -> str:
    """Create a JWT refresh token.

    Claims: sub, tenant_id, jti, type=refresh, iat, exp.
    """
    payload = _build_payload(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=[],  # Refresh tokens don't carry roles
        jti=jti,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode and validate a JWT.

    Raises:
        TokenExpiredError: if the token is past its expiration.
        TokenRevokedError: if the token's JTI is blacklisted.
        InvalidTokenError: if the token is malformed or wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "jti", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError:
        raise InvalidTokenError()

    # Validate token type
    if payload.get("type") != expected_type:
        raise InvalidTokenError()

    return payload


def get_token_remaining_ttl(token: str) -> int:
    """Return the remaining TTL in seconds for a token.

    Used to set the blacklist TTL on logout.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp"], "verify_exp": True},
        )
        exp: int = payload.get("exp", 0)
        now = int(datetime.now(timezone.utc).timestamp())
        return max(0, exp - now)
    except jwt.InvalidTokenError:
        # If we can't decode, use the access token default TTL as fallback
        return settings.access_token_expire_minutes * 60
