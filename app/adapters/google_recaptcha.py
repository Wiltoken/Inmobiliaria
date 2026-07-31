"""Google reCAPTCHA v3 adapter + mock verifier when disabled."""

from __future__ import annotations

import httpx

from app.config import settings
from app.ports.captcha import CaptchaVerificationError, CaptchaVerifier


class GoogleRecaptchaVerifier(CaptchaVerifier):
    """Google reCAPTCHA v3 verification adapter.

    Calls the Google siteverify API and checks the returned score against
    the configured threshold. Requires recaptcha_enabled=True and valid
    site/secret keys in settings.
    """

    _VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

    async def verify(self, token: str, client_ip: str) -> bool:
        """Verify a reCAPTCHA v3 token against Google siteverify API.

        Returns True if score >= settings.recaptcha_score_threshold.
        Raises CaptchaVerificationError on network/service errors.
        """
        if not settings.recaptcha_enabled:
            # Should never be called when disabled — gate at the injection point
            return True

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self._VERIFY_URL,
                    data={
                        "secret": settings.recaptcha_secret_key,
                        "response": token,
                        "remoteip": client_ip,
                    },
                )
            except httpx.TimeoutException as exc:
                raise CaptchaVerificationError(
                    f"reCAPTCHA verification timed out: {exc}"
                ) from exc
            except httpx.HTTPError as exc:
                raise CaptchaVerificationError(
                    f"reCAPTCHA verification request failed: {exc}"
                ) from exc

        data = response.json()

        if not data.get("success", False):
            # Token rejected by Google outright
            return False

        score = data.get("score", 0.0)
        threshold = settings.recaptcha_score_threshold

        return score >= threshold


class MockCaptchaVerifier(CaptchaVerifier):
    """Mock CAPTCHA verifier — always returns True.

    Used when recaptcha_enabled=False so the login endpoint does not
    need to branch on the flag.
    """

    async def verify(self, token: str, client_ip: str) -> bool:
        """Always return True — no actual verification."""
        return True


def get_captcha_verifier() -> CaptchaVerifier:
    """Factory: return the appropriate verifier based on settings.

    When disabled (or no secret key), returns the mock so login code
    can call verify() unconditionally without None checks.
    """
    if settings.recaptcha_enabled and settings.recaptcha_secret_key:
        return GoogleRecaptchaVerifier()
    return MockCaptchaVerifier()
