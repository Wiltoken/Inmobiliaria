"""Unit tests for app.core.security — password hashing and JWT operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.exceptions import InvalidTokenError, PasswordPolicyError, TokenExpiredError
from app.core.security import (
    ALGORITHM,
    PolicyViolation,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_remaining_ttl,
    hash_password,
    hash_token,
    validate_password,
    verify_password,
)


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #

class TestValidatePassword:
    """Tests for validate_password()."""

    def test_valid_password_min_length(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Password meeting minimum length passes validation."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=8,
                password_require_special=False,
            ),
        )
        violations = validate_password("ValidPass1")
        assert violations == []

    def test_valid_password_with_special(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Password with special character passes when required."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=8,
                password_require_special=True,
            ),
        )
        violations = validate_password("ValidPass1!")
        assert violations == []

    def test_password_too_short(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Password below minimum length fails with a PolicyViolation."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=8,
                password_require_special=False,
            ),
        )
        violations = validate_password("Short1!")
        assert len(violations) == 1
        assert violations[0].field == "password"
        assert "8 characters" in violations[0].message

    def test_password_missing_special(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Password without special character fails when required."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=8,
                password_require_special=True,
            ),
        )
        violations = validate_password("ValidPass1")
        assert len(violations) == 1
        assert "special character" in violations[0].message

    def test_password_multiple_violations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Short password without special character returns two violations."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=8,
                password_require_special=True,
            ),
        )
        violations = validate_password("Short1")
        assert len(violations) == 2


class TestHashPassword:
    """Tests for hash_password()."""

    def test_hash_password_returns_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """hash_password returns a non-empty bcrypt hash string."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=4,
                password_require_special=False,
            ),
        )
        hashed = hash_password("anypassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_hash_password_policy_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """hash_password raises PasswordPolicyError for non-compliant passwords."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=10,
                password_require_special=True,
            ),
        )
        with pytest.raises(PasswordPolicyError):
            hash_password("short1!")


class TestHashToken:
    """Tests for hash_token() — machine-generated tokens bypass policy."""

    def test_hash_token_returns_string(self) -> None:
        """hash_token returns a bcrypt hash without policy validation."""
        hashed = hash_token("random-machine-token-abc123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")

    def test_hash_token_skips_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """hash_token does NOT raise even with a very short token."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=100,
                password_require_special=True,
            ),
        )
        # Should not raise — tokens bypass policy
        hashed = hash_token("x")
        assert hashed.startswith("$2b$")


class TestVerifyPassword:
    """Tests for verify_password()."""

    def test_verify_password_correct(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """verify_password returns True for correct password."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=4,
                password_require_special=False,
            ),
        )
        hashed = hash_password("MyTestPass123")
        assert verify_password("MyTestPass123", hashed) is True

    def test_verify_password_incorrect(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """verify_password returns False for incorrect password."""
        from app.config import AuthSettings

        monkeypatch.setattr(
            "app.core.security.settings",
            AuthSettings(
                secret_key="test-secret",
                database_url="sqlite+aiosqlite:///:memory:",
                redis_url="redis://localhost:6379/0",
                password_min_length=4,
                password_require_special=False,
            ),
        )
        hashed = hash_password("MyTestPass123")
        assert verify_password("WrongPassword", hashed) is False


class TestPolicyViolation:
    """Tests for PolicyViolation.to_dict()."""

    def test_to_dict_returns_field_and_message(self) -> None:
        """to_dict returns a dict with field and message keys."""
        pv = PolicyViolation("password", "Too short")
        d = pv.to_dict()
        assert d == {"field": "password", "message": "Too short"}


# --------------------------------------------------------------------------- #
# JWT operations
# --------------------------------------------------------------------------- #

class TestCreateAccessToken:
    """Tests for create_access_token()."""

    def test_create_access_token_returns_jwt_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_access_token returns a valid HS256 JWT."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["user"],
            jti="test-jti-123",
        )

        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 3

        # Verify header via unverified header (doesn't verify signature)
        unverified_header = jwt.get_unverified_header(token)
        assert unverified_header["alg"] == ALGORITHM
        assert unverified_header["typ"] == "JWT"

    def test_access_token_contains_correct_claims(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Access token includes sub, tenant_id, roles, jti, type, iat, exp."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        jti = "my-jti-456"
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["admin", "user"],
            jti=jti,
        )

        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["roles"] == ["admin", "user"]
        assert payload["jti"] == jti
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_access_token_expiry_is_15_minutes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Access token exp is set to 15 minutes from now."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        before = datetime.now(timezone.utc)
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["user"],
            jti="test-jti",
        )
        after = datetime.now(timezone.utc)

        payload = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # exp should be approximately 15 minutes after iat
        delta = exp - iat
        assert timedelta(minutes=14, seconds=55) <= delta <= timedelta(minutes=15, seconds=5)


class TestCreateRefreshToken:
    """Tests for create_refresh_token()."""

    def test_refresh_token_returns_jwt_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_refresh_token returns a valid HS256 JWT."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
            jti="refresh-jti-789",
        )

        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 3

    def test_refresh_token_type_is_refresh(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Refresh token has type=refresh and empty roles."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
            jti="refresh-jti",
        )

        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["type"] == "refresh"
        assert payload["roles"] == []

    def test_refresh_token_expiry_is_7_days(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Refresh token exp is set to 7 days from iat."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
            jti="refresh-jti",
        )

        payload = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        delta = exp - iat
        assert timedelta(days=6, hours=23) <= delta <= timedelta(days=7, seconds=5)


class TestDecodeToken:
    """Tests for decode_token()."""

    def test_decode_valid_access_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """decode_token returns claims dict for a valid access token."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["user"],
            jti="decode-test-jti",
        )

        payload = decode_token(token, expected_type="access")
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_decode_wrong_type_raises_invalid_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """decode_token raises InvalidTokenError when expected_type doesn't match."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        access_token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["user"],
            jti="wrong-type-jti",
        )

        with pytest.raises(InvalidTokenError):
            decode_token(access_token, expected_type="refresh")

    def test_decode_malformed_token_raises_invalid_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """decode_token raises InvalidTokenError for a non-JWT string."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        with pytest.raises(InvalidTokenError):
            decode_token("not.a.jwt.token", expected_type="access")

    def test_decode_expired_token_raises_token_expired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """decode_token raises TokenExpiredError for an expired token."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        # Create a token that expired 1 hour ago
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": ["user"],
            "jti": "expired-jti",
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            payload,
            test_settings.secret_key,
            algorithm=ALGORITHM,
        )

        with pytest.raises(TokenExpiredError):
            decode_token(expired_token, expected_type="access")


class TestGetTokenRemainingTtl:
    """Tests for get_token_remaining_ttl()."""

    def test_ttl_returns_positive_for_fresh_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_token_remaining_ttl returns remaining seconds for a valid token."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=["user"],
            jti="ttl-test-jti",
        )

        ttl = get_token_remaining_ttl(token)
        # Should be close to 15 * 60 = 900 seconds
        assert 890 <= ttl <= 900

    def test_ttl_returns_fallback_for_invalid_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_token_remaining_ttl returns fallback TTL for a token signed with wrong secret."""
        from app.config import AuthSettings

        test_settings = AuthSettings(
            secret_key="test-secret-key-minimum-256-bits-long-for-hs256!!",
            database_url="sqlite+aiosqlite:///:memory:",
            redis_url="redis://localhost:6379/0",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )
        monkeypatch.setattr("app.core.security.settings", test_settings)

        # Token signed with wrong secret — can't decode, returns fallback
        payload = {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "roles": ["user"],
            "jti": "bad-jti",
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        bad_token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)

        # Should not raise, but return the fallback (access_token_expire_minutes * 60)
        ttl = get_token_remaining_ttl(bad_token)
        assert ttl == 15 * 60  # fallback is 900 seconds
