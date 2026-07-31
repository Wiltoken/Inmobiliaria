"""FastAPI application skeleton with lifespan events and health endpoints."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.middleware import (
    AuditLogMiddleware,
    AuthMiddleware,
    RBACMiddleware,
    RateLimitMiddleware,
)
from app.logging import configure_logging

# Configure structlog at import time
configure_logging()

# Module-level logger — configured once at startup
log = structlog.get_logger()


# --------------------------------------------------------------------------- #
# Lifespan: manage DB engine + Redis connection pool per worker
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: verify DB pool + Redis. Teardown: close pools."""
    log.info("startup", env=settings.app_env, log_level=settings.log_level)

    # Quick sanity checks — don't crash if services aren't up yet
    try:
        from app.adapters.redis_client import get_redis_client
        redis = get_redis_client()
        await redis.ping()
        log.info("redis_connected", url=settings.redis_url)
    except Exception as exc:
        log.warning("redis_unavailable_at_startup", error=str(exc))

    yield

    log.info("shutdown")
    try:
        from app.adapters.redis_client import close_redis_client
        from app.adapters.database import close_engine
        await close_redis_client()
        await close_engine()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# FastAPI app
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="inmobiliaria-platform",
    version="0.1.0",
    description="Inmobiliaria platform — FastAPI async + SQLAlchemy 2.0 + PostgreSQL/PostGIS + Redis",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware stack (FastAPI executes in reverse order of addition) ──────────
# Order desired: CORS → AuditLog → RateLimit → Auth → RBAC
# Add in reverse order so they execute in the correct sequence:
app.add_middleware(RBACMiddleware)       # 5. RBAC — last to add, first to run
app.add_middleware(AuthMiddleware)      # 4. Auth — validates tokens
app.add_middleware(RateLimitMiddleware) # 3. RateLimit — token bucket per IP
app.add_middleware(AuditLogMiddleware)  # 2. AuditLog — logs auth events
app.add_middleware(                     # 1. CORS — first to add, last to run
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Health endpoints (no auth required)
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — process is alive."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> Response:
    """Readiness probe — DB pool + Redis are both reachable."""
    from sqlalchemy import text

    errors: list[str] = []

    # Check DB
    try:
        from app.adapters.database import get_engine
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("db_readiness_check_failed", error=str(exc))
        errors.append(f"db: {exc}")

    # Check Redis
    try:
        from app.adapters.redis_client import get_redis_client
        redis_client = get_redis_client()
        await redis_client.ping()
    except Exception as exc:
        log.warning("redis_readiness_check_failed", error=str(exc))
        errors.append(f"redis: {exc}")

    if errors:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "errors": errors},
        )
    return JSONResponse(content={"status": "ready"})


# --------------------------------------------------------------------------- #
# Global request ID middleware
# --------------------------------------------------------------------------- #
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for traceability."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# --------------------------------------------------------------------------- #
# API v1 router
# --------------------------------------------------------------------------- #
from app.api.v1.router import api_router

app.include_router(api_router)


# --------------------------------------------------------------------------- #
# App factory for tests
# --------------------------------------------------------------------------- #
def create_app() -> FastAPI:
    """Factory for tests — returns fully-wired app without re-running lifespan."""
    return app
