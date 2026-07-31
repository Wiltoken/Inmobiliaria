"""Middleware stack: CORS → AuditLog → RateLimit → Auth → RBAC.

All security thresholds from settings — zero hardcoded literals.
Middleware skips auth/rate-limit on /health, /health/ready, /docs, /openapi.json, /api/v1/auth/*.
"""

from __future__ import annotations

import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.adapters.redis_client import (
    is_token_blacklisted,
    rate_limit_check,
)
from app.config import settings

log = structlog.get_logger()

# Paths that bypass auth and rate-limiting
PUBLIC_PATHS = frozenset([
    "/health",
    "/health/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
])


def _is_public_path(path: str) -> bool:
    """Return True if the path should skip auth (docs, health, etc)."""
    if path in PUBLIC_PATHS:
        return True
    return False


def _is_auth_skipped_path(path: str) -> bool:
    """Return True if auth middleware should skip this path (public auth endpoints)."""
    return _is_public_path(path) or path.startswith("/api/v1/auth")


def _client_ip(request: Request) -> str:
    """Extract the real client IP, checking X-Forwarded-For first."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first (original) IP
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ── Audit Log Middleware ──────────────────────────────────────────────────────


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Fire-and-forget audit log on every authenticated request.

    Runs after the response is ready so it does not block the auth response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Determine action from path/method
        action = _action_from_request(request)

        # Only log meaningful auth events (skip static assets, health, etc.)
        if action and not _is_public_path(request.url.path):
            user_id: str | None = None
            tenant_id: str | None = None

            # Try to get from request.state if set by AuthMiddleware
            if hasattr(request.state, "user_id"):
                user_id = str(request.state.user_id)
            if hasattr(request.state, "tenant_id"):
                tenant_id = str(request.state.tenant_id)

            # Fire-and-forget audit write
            await self._write_log(
                action=action,
                user_id=user_id,
                tenant_id=tenant_id,
                ip_address=_client_ip(request),
                request_id=getattr(request.state, "request_id", None),
                status_code=response.status_code,
            )

        return response

    async def _write_log(
        self,
        action: str,
        user_id: str | None,
        tenant_id: str | None,
        ip_address: str,
        request_id: str | None,
        status_code: int,
    ) -> None:
        """Write audit log entry to DB.

        NOTE: This is a fire-and-forget inline write per the design decision.
        In production, consider offloading to a background queue if latency is a concern.
        """
        try:
            # Import here to avoid circular refs and allow lifespan to init DB first
            from app.adapters.database import get_session_maker
            from app.domain.models import AuditLog

            session_maker = get_session_maker()
            async with session_maker() as session:
                log_entry = AuditLog(
                    user_id=user_id and __import__("uuid").UUID(user_id) or None,
                    tenant_id=tenant_id and __import__("uuid").UUID(tenant_id) or None,
                    action=action,
                    ip_address=ip_address,
                    details={
                        "request_id": request_id,
                        "status_code": status_code,
                    },
                )
                session.add(log_entry)
                await session.commit()
        except Exception as exc:
            # Never let audit logging failure affect the response
            structlog.get_logger().warning(
                "audit_log_write_failed",
                action=action,
                error=str(exc),
            )


def _action_from_request(request: Request) -> str | None:
    """Map a request to an audit action name."""
    path = request.url.path
    method = request.method

    if path == "/api/v1/auth/login" and method == "POST":
        return "login_attempt"
    if path == "/api/v1/auth/refresh" and method == "POST":
        return "token_refresh"
    if path == "/api/v1/auth/logout" and method == "POST":
        return "logout"

    # Generic action for authenticated requests
    if hasattr(request.state, "user_id") and request.state.user_id:
        if path.startswith("/api/v1/admin"):
            return f"admin_{method.lower()}"
        return f"api_{method.lower()}"

    return None


# ── Rate Limit Middleware ──────────────────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiter per IP address.

    Returns 429 Too Many Requests with Retry-After header when limit exceeded.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only skip rate limiting for truly static/public paths (docs, health).
        # Auth endpoints (/api/v1/auth/*) MUST be rate-limited.
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        ip = _client_ip(request)
        allowed, remaining = await rate_limit_check(
            ip_address=ip,
            max_requests=settings.rate_limit_requests_per_second,
            window_seconds=settings.rate_limit_window_seconds,
        )

        if not allowed:
            log.warning("rate_limit_exceeded", ip=ip)
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": settings.rate_limit_window_seconds,
                },
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


# ── Auth Middleware ───────────────────────────────────────────────────────────


class AuthMiddleware(BaseHTTPMiddleware):
    """Extract Bearer token, decode, check blacklist, attach user to request.state.

    Skips auth for public paths.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if _is_auth_skipped_path(request.url.path):
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # No token — let the dependency injection handle 401
            return await call_next(request)

        token = auth_header[7:]  # Strip "Bearer "

        # Decode and validate token (will raise if invalid)
        try:
            from app.core.security import decode_token

            claims = decode_token(token, expected_type="access")

            # Check blacklist
            jti = claims.get("jti")
            if jti and await is_token_blacklisted(jti):
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Token has been revoked",
                        "error_code": "AUTH_TOKEN_REVOKED",
                    },
                )

            # Attach user info to request.state for downstream use
            request.state.user_id = uuid.UUID(claims["sub"])
            request.state.tenant_id = uuid.UUID(claims["tenant_id"])
            request.state.roles = claims.get("roles", [])
            request.state.jti = jti
            request.state.token = token

        except Exception:
            # Let the dependency handle 401
            pass

        return await call_next(request)


# ── RBAC Middleware ───────────────────────────────────────────────────────────


class RBACMiddleware(BaseHTTPMiddleware):
    """Check user roles against endpoint-required roles.

    Endpoint role requirements are stored in request.state.rbac_required_roles.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        required_roles = getattr(request.state, "rbac_required_roles", None)

        if required_roles is None:
            # No RBAC check required for this endpoint
            return await call_next(request)

        user_roles: list[str] = getattr(request.state, "roles", [])
        if not any(role in user_roles for role in required_roles):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Insufficient permissions",
                    "error_code": "AUTH_INSUFFICIENT_ROLE",
                    "required_roles": required_roles,
                },
            )

        return await call_next(request)
