"""Integration tests for Redis token-bucket rate limiter."""

from __future__ import annotations

import time as time_module

import pytest
import pytest_asyncio

from app.adapters.redis_client import (
    RATE_LIMIT_PREFIX,
    rate_limit_check,
    rate_limit_key,
)


# --------------------------------------------------------------------------- #
# FakeRedis time() patch — fakeredis returns (sec, microsec) tuple,
# but redis-py returns float seconds.  We patch per-test so the app code
# (which expects float) works correctly.
# --------------------------------------------------------------------------- #

class FakeRedisWithTime:
    """Wrapper that makes FakeRedis.time() return a float like real redis-py."""

    def __init__(self, fake_redis) -> None:
        self._redis = fake_redis

    async def time(self) -> float:
        """Return unix timestamp as float (like real redis-py)."""
        return time_module.time()

    async def zadd(self, *args, **kwargs) -> int:
        return await self._redis.zadd(*args, **kwargs)

    async def zremrangebyscore(self, *args, **kwargs) -> int:
        return await self._redis.zremrangebyscore(*args, **kwargs)

    async def zcard(self, *args, **kwargs) -> int:
        return await self._redis.zcard(*args, **kwargs)

    async def expire(self, *args, **kwargs) -> bool:
        return await self._redis.expire(*args, **kwargs)

    def pipeline(self):
        """Return a pipeline directly (not a coroutine in fakeredis)."""
        return self._redis.pipeline()

    def __getattr__(self, name):
        return getattr(self._redis, name)


# --------------------------------------------------------------------------- #
# Token bucket tests using fakeredis
# --------------------------------------------------------------------------- #

class TestRateLimitTokenBucket:
    """Tests for rate_limit_check — Redis token-bucket implementation."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_limit(self) -> None:
        """Requests within the limit are allowed."""
        import fakeredis.aioredis
        import app.adapters.redis_client as redis_module

        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        fake_with_time = FakeRedisWithTime(fake)
        redis_module._client = fake_with_time

        ip = "192.168.1.100"
        allowed, remaining = await rate_limit_check(
            ip_address=ip,
            max_requests=5,
            window_seconds=10,
        )
        assert allowed is True
        assert remaining == 4  # 5 - 1

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_after_exceeded(self) -> None:
        """Requests exceeding the limit are blocked (allowed=False)."""
        import fakeredis.aioredis
        import app.adapters.redis_client as redis_module

        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        fake_with_time = FakeRedisWithTime(fake)
        redis_module._client = fake_with_time

        ip = "192.168.1.101"
        max_requests = 3
        window_seconds = 10

        # Fill the bucket
        for i in range(max_requests):
            allowed, remaining = await rate_limit_check(
                ip_address=ip,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            assert allowed is True

        # The 4th request should be blocked
        allowed, remaining = await rate_limit_check(
            ip_address=ip,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_rate_limit_remaining_decrements(self) -> None:
        """Remaining count decrements with each request within the limit."""
        import fakeredis.aioredis
        import app.adapters.redis_client as redis_module

        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        fake_with_time = FakeRedisWithTime(fake)
        redis_module._client = fake_with_time

        ip = "192.168.1.102"
        max_requests = 5
        window_seconds = 10

        expected_remaining = [4, 3, 2, 1, 0]
        for expected in expected_remaining:
            allowed, remaining = await rate_limit_check(
                ip_address=ip,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            assert allowed is True
            assert remaining == expected

    @pytest.mark.asyncio
    async def test_rate_limit_different_ips_independent(self) -> None:
        """Two different IPs have independent rate limit buckets."""
        import fakeredis.aioredis
        import app.adapters.redis_client as redis_module

        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        fake_with_time = FakeRedisWithTime(fake)
        redis_module._client = fake_with_time

        ip_a = "10.0.0.1"
        ip_b = "10.0.0.2"
        max_requests = 2
        window_seconds = 10

        # Exhaust bucket for IP A
        await rate_limit_check(ip_address=ip_a, max_requests=max_requests, window_seconds=window_seconds)
        await rate_limit_check(ip_address=ip_a, max_requests=max_requests, window_seconds=window_seconds)

        # IP B should still have capacity
        allowed, remaining = await rate_limit_check(
            ip_address=ip_b, max_requests=max_requests, window_seconds=window_seconds
        )
        assert allowed is True
        assert remaining == 1

    @pytest.mark.asyncio
    async def test_rate_limit_exact_limit_allowed(self) -> None:
        """Request number exactly equal to max_requests is still allowed."""
        import fakeredis.aioredis
        import app.adapters.redis_client as redis_module

        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        fake_with_time = FakeRedisWithTime(fake)
        redis_module._client = fake_with_time

        ip = "192.168.1.200"
        max_requests = 3

        # Make exactly max_requests requests
        for _ in range(max_requests):
            allowed, _ = await rate_limit_check(
                ip_address=ip,
                max_requests=max_requests,
                window_seconds=10,
            )
            assert allowed is True

        # Next one is blocked
        allowed, _ = await rate_limit_check(
            ip_address=ip,
            max_requests=max_requests,
            window_seconds=10,
        )
        assert allowed is False
