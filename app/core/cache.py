"""Redis cache utilities for DemeterAI.

Provides a shared async Redis client for caching and job tracking.
"""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis  # type: ignore[import-not-found]

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _create_client() -> Redis:
    """Create a Redis client using application settings."""
    logger.info("Initializing Redis client", extra={"redis_url": settings.REDIS_URL})
    return Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )


def get_redis_client() -> Redis:
    """Get singleton Redis client instance."""
    return _create_client()


async def close_redis_client() -> None:
    """Close Redis client (used for application shutdown)."""
    client = _create_client()
    await client.close()
