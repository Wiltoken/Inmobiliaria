"""Async Redis client with connection pooling and all required key operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from redis.asyncio import ConnectionPool, Redis

if TYPE_CHECKING:
    import uuid

from app.config import settings

_pool: ConnectionPool | None = None
_client: Redis | None = None


def get_redis_pool() -> ConnectionPool:
    """Return shared async connection pool, creating on first call."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis_client() -> Redis:
    """Return shared async Redis client backed by the shared pool."""
    global _client
    if _client is None:
        _client = Redis(connection_pool=get_redis_pool())
    return _client


async def close_redis_client() -> None:
    """Disconnect and dispose pool on shutdown."""
    global _client, _pool
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


# --------------------------------------------------------------------------- #
# Redis key helpers — one source of truth for key naming
# --------------------------------------------------------------------------- #

BLACKLIST_PREFIX = "blacklist"
RATE_LIMIT_PREFIX = "rate_limit"
REFRESH_PREFIX = "refresh"
LAST_ACTIVE_PREFIX = "last_active"
MATCH_PREFIX = "match"


def blacklist_key(jti: str) -> str:
    return f"{BLACKLIST_PREFIX}:{jti}"


def rate_limit_key(ip_address: str) -> str:
    return f"{RATE_LIMIT_PREFIX}:{ip_address}"


def refresh_key(user_id: str, jti: str) -> str:
    return f"{REFRESH_PREFIX}:{user_id}:{jti}"


def last_active_key(user_id: str) -> str:
    return f"{LAST_ACTIVE_PREFIX}:{user_id}"


# --------------------------------------------------------------------------- #
# Redis operations
# --------------------------------------------------------------------------- #

async def redis_get(key: str) -> str | None:
    """Get a string value."""
    return await get_redis_client().get(key)


async def redis_set(key: str, value: str, ex_seconds: int | None = None) -> bool:
    """Set a string value with optional TTL in seconds."""
    return await get_redis_client().set(key, value, ex=ex_seconds)


async def redis_setex(key: str, value: str, ex_seconds: int) -> bool:
    """Set a string value with TTL in seconds."""
    return await get_redis_client().setex(key, ex_seconds, value)


async def redis_expire(key: str, ex_seconds: int) -> bool:
    """Set/refresh TTL on an existing key."""
    return await get_redis_client().expire(key, ex_seconds)


async def redis_delete(*keys: str) -> int:
    """Delete one or more keys. Returns number of keys deleted."""
    if not keys:
        return 0
    return await get_redis_client().delete(*keys)


async def redis_exists(key: str) -> bool:
    """Check if a key exists."""
    return await get_redis_client().exists(key) > 0


# --------------------------------------------------------------------------- #
# Token bucket rate limiter
# --------------------------------------------------------------------------- #

async def rate_limit_check(
    ip_address: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """Token-bucket rate limit check.

    Returns (allowed: bool, remaining: int).
    Uses Redis sorted set with timestamps as scores.
    """
    client = get_redis_client()
    key = rate_limit_key(ip_address)
    now_ts: float = await client.time()
    now_ms = int(now_ts * 1000)
    window_start = now_ms - (window_seconds * 1000)

    pipe = client.pipeline()
    # Remove entries outside the window
    pipe.zremrangebyscore(key, 0, window_start)
    # Add current request with timestamp as score
    pipe.zadd(key, {f"{now_ms}": now_ts})
    # Count requests in window
    pipe.zcard(key)
    # Set TTL on the key so abandoned keys auto-cleanup
    pipe.expire(key, window_seconds + 1)
    results = await pipe.execute()
    count = results[2]  # zcard result

    allowed = count <= max_requests
    remaining = max(0, max_requests - count)
    return allowed, remaining


# --------------------------------------------------------------------------- #
# Session / activity tracking
# --------------------------------------------------------------------------- #

async def touch_last_active(user_id: str, ttl_seconds: int) -> None:
    """Update or create the last-active key with a fresh TTL (sliding window)."""
    await redis_setex(last_active_key(user_id), str(__import__("time").time()), ttl_seconds)


async def is_last_active_expired(user_id: str) -> bool:
    """Return True if the session has expired (key missing)."""
    return not await redis_exists(last_active_key(user_id))


# --------------------------------------------------------------------------- #
# Token blacklist (revoked JTIs)
# --------------------------------------------------------------------------- #

async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a JTI to the blacklist with TTL matching the access token lifetime."""
    await redis_setex(blacklist_key(jti), "1", ttl_seconds)


async def is_token_blacklisted(jti: str) -> bool:
    """Return True if the token JTI is blacklisted."""
    return await redis_exists(blacklist_key(jti))


# --------------------------------------------------------------------------- #
# Refresh token storage
# --------------------------------------------------------------------------- #

async def store_refresh_token(user_id: str, jti: str, ttl_seconds: int) -> None:
    """Store a valid refresh token in Redis with TTL."""
    await redis_setex(refresh_key(user_id, jti), "1", ttl_seconds)


async def revoke_refresh_token(user_id: str, jti: str) -> None:
    """Remove a single refresh token (used during rotation)."""
    await redis_delete(refresh_key(user_id, jti))


async def revoke_all_user_refresh_tokens(user_id: str) -> int:
    """Revoke all refresh tokens for a user (used during password reset)."""
    client = get_redis_client()
    pattern = f"{REFRESH_PREFIX}:{user_id}:*"
    keys: list[str] = []
    async for key in client.scan_iter(match=pattern):
        keys.append(key)
    return await redis_delete(*keys) if keys else 0


async def is_refresh_token_valid(user_id: str, jti: str) -> bool:
    """Return True if the refresh token exists in Redis (not revoked)."""
    return await redis_exists(refresh_key(user_id, jti))


# --------------------------------------------------------------------------- #
# Match result cache
# --------------------------------------------------------------------------- #

def match_cache_key(buyer_id: str | uuid.UUID) -> str:
    """Redis key for cached buyer match results."""
    return f"{MATCH_PREFIX}:{buyer_id}"


async def cache_matches(buyer_id: str | uuid.UUID, matches: list[dict], ttl_seconds: int | None = None) -> None:
    """Cache a buyer's match results in Redis.

    Args:
        buyer_id: Buyer's user ID.
        matches: List of match dicts (serializable to JSON).
        ttl_seconds: TTL in seconds. Defaults to MATCH_CACHE_TTL_SECONDS from settings.
    """
    import json

    if ttl_seconds is None:
        from app.config import settings
        ttl_seconds = getattr(settings, "match_cache_ttl_seconds", 3600)

    key = match_cache_key(buyer_id)
    value = json.dumps(matches, default=str)
    await redis_setex(key, value, ttl_seconds)


async def get_cached_matches(buyer_id: str | uuid.UUID) -> list[dict] | None:
    """Get cached match results from Redis.

    Returns None if cache miss or parse error.
    """
    import json

    key = match_cache_key(buyer_id)
    value = await redis_get(key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


async def invalidate_match_cache(buyer_id: str | uuid.UUID) -> None:
    """Delete cached matches for a buyer."""
    key = match_cache_key(buyer_id)
    await redis_delete(key)
