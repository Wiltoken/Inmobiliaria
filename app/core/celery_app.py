"""Celery application configuration with beat schedule for periodic tasks."""

from __future__ import annotations

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

# ── Broker & Result Backend ────────────────────────────────────────────────────

broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
result_backend = os.getenv("REDIS_URL", "redis://redis:6379/0")

# ── Serialization ──────────────────────────────────────────────────────────────

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

# ── Task Configuration ─────────────────────────────────────────────────────────

task_track_started = True
task_time_limit = 3600  # 1 hour max per task
task_soft_time_limit = 3000  # 50 minutes soft limit
task_acks_late = True
task_reject_on_worker_lost = True

# Retry policy
task_default_retry_delay = 60  # 1 minute
task_max_retries = 3

# ── Worker Configuration ───────────────────────────────────────────────────────

worker_prefetch_multiplier = 4
worker_concurrency = int(os.getenv("CELERY_CONCURRENCY", "4"))
worker_max_tasks_per_child = 1000  # Recycle workers to prevent memory leaks

# ── Beat Schedule ─────────────────────────────────────────────────────────────

beat_schedule = {
    # NOTE: database backups are handled by scripts/backup.sh (run inside the
    # postgres container via `make backup` / a host cron), NOT by Celery — the
    # worker image has neither pg_dump nor the /backups volume.
    # Cleanup old matches every 6 hours
    "cleanup-old-matches": {
        "task": "app.core.celery_app.tasks.cleanup_old_matches",
        "schedule": crontab(hour="*/6", minute=0),
        "options": {"queue": "maintenance"},
    },
    # Recompute all matches daily at 3:00 AM UTC
    "recompute-all-matches": {
        "task": "app.core.celery_app.tasks.match_recompute",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "matching"},
    },
    # Token cleanup every hour
    "cleanup-expired-tokens": {
        "task": "app.core.celery_app.tasks.cleanup_expired_tokens",
        "schedule": crontab(minute=0),
        "options": {"queue": "maintenance"},
    },
}


# ── Celery App Instance ────────────────────────────────────────────────────────

celery_app = Celery(
    "inmobiliaria",
    broker=broker_url,
    backend=result_backend,
)

# Configure from object (Celery 5.x style)
celery_app.config_from_object(
    "app.core.celery_app"
)

# ── Periodic Tasks ─────────────────────────────────────────────────────────────


@celery_app.task(name="app.core.celery_app.tasks.cleanup_old_matches")
def cleanup_old_matches() -> dict:
    """Remove stale match records older than MATCH_CACHE_TTL_SECONDS.

    Returns:
        dict with cleanup status and count of deleted records.
    """
    from datetime import datetime, timezone

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import create_async_engine

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://inmuebles:changeme@postgres:5432/inmobiliaria_db",
    )

    async def _cleanup():
        engine = create_async_engine(database_url, echo=False)
        async with engine.begin() as conn:
            # Delete matches older than cache TTL (default 24 hours)
            ttl_hours = int(os.getenv("MATCH_CACHE_TTL_SECONDS", "86400")) // 3600
            cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)

            result = await conn.execute(
                delete(Match).where(Match.computed_at < cutoff)  # type: ignore
            )
            return result.rowcount

    # Import here to avoid circular imports
    from app.domain.models import Match

    try:
        import asyncio
        deleted = asyncio.run(_cleanup())
        return {"status": "success", "deleted_count": deleted}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="app.core.celery_app.tasks.match_recompute")
def match_recompute() -> dict:
    """Recompute matches for all active buyers.

    This is a long-running task that should run during off-peak hours.

    Returns:
        dict with recompute status and count of buyers processed.
    """
    import uuid

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.matching import compute_all_matches
    from app.domain.models import BuyerProfile

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://inmuebles:changeme@postgres:5432/inmobiliaria_db",
    )

    async def _recompute():
        engine = create_async_engine(database_url, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute(select(BuyerProfile.id))
            buyer_ids = result.scalars().all()

        processed = 0
        errors = 0

        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        for buyer_id in buyer_ids:
            try:
                async with async_session() as session:
                    await compute_all_matches(uuid.UUID(str(buyer_id)), session)
                    await session.commit()
                processed += 1
            except Exception:
                errors += 1

        await engine.dispose()
        return {"processed": processed, "errors": errors}

    try:
        import asyncio
        result = asyncio.run(_recompute())
        return {"status": "success", **result}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="app.core.celery_app.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> dict:
    """Clean up expired refresh tokens from the database.

    Returns:
        dict with cleanup status and count of deleted records.
    """
    from datetime import datetime, timezone

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.domain.models import RefreshToken

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://inmuebles:changeme@postgres:5432/inmobiliaria_db",
    )

    async def _cleanup():
        engine = create_async_engine(database_url, echo=False)
        async with engine.begin() as conn:
            result = await conn.execute(
                delete(RefreshToken).where(
                    RefreshToken.expires_at < datetime.now(timezone.utc)
                )
            )
            return result.rowcount

    try:
        import asyncio
        deleted = asyncio.run(_cleanup())
        return {"status": "success", "deleted_count": deleted}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
