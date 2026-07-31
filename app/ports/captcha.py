"""ABC port for CAPTCHA verification — allows pluggable adapters (Google, hCaptcha, etc.)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CaptchaVerifier(ABC):
    """Abstract CAPTCHA verifier port.

    Adapters implement verify() to call their respective verification API.
    The login endpoint depends on this abstraction so CAPTCHA can be
    toggled on/off without changing the endpoint logic.
    """

    @abstractmethod
    async def verify(self, token: str, client_ip: str) -> bool:
        """Verify a CAPTCHA token.

        Args:
            token: The CAPTCHA token submitted by the client.
            client_ip: The client's IP address (passed to the verification API).

        Returns:
            True if the token is valid and score meets threshold; False otherwise.

        Raises:
            CaptchaVerificationError: If the verification service is unavailable
                or returns an unexpected error (network timeout, etc.).
        """
        ...


class CaptchaVerificationError(Exception):
    """Raised when CAPTCHA verification cannot be completed due to a service error."""

    pass
