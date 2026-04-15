"""
Redis caching helpers for analysis endpoints.

Pattern
-------
- Every cached value is stored as a JSON string under a computed key.
- Keys are registered in a per-user Redis Set so they can all be invalidated
  at once (e.g. when a job completes and the user's aggregates change).
- TTL: 5 minutes for "live" analysis data; completed job summaries get 1 hour.

Usage
-----
    from cache import get_cached, set_cached, invalidate_user_cache

    cached = get_cached(key)
    if cached is not None:
        return cached

    data = expensive_db_query()
    set_cached(key, data, ttl=300, user_id=user.id)
    return data
"""

import json
from typing import Any
from redis import Redis
from config import settings
from logger import logger

# Shared Redis connection (same host/port used by the RQ worker).
_redis: Redis = Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

# Redis Set that tracks all active cache keys for a given user.
_USER_KEYS_SET = "user:{user_id}:cache_keys"

# Default TTLs pulled from settings so they are tunable via env vars.
TTL_ANALYSIS: int = settings.cache_ttl_analysis
TTL_JOB_SUMMARY: int = settings.cache_ttl_job_summary


def _user_keys_set(user_id: str) -> str:
    return _USER_KEYS_SET.format(user_id=user_id)


def get_cached(key: str) -> Any | None:
    """Return deserialized cached value, or None on miss / Redis error."""
    try:
        raw = _redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"[Cache] GET failed for key={key!r}: {exc}")
        return None


def set_cached(key: str, data: Any, *, ttl: int = TTL_ANALYSIS, user_id: str | None = None) -> None:
    """
    Serialize and store data under key with the given TTL.
    If user_id is provided, register key in the user's tracking set
    so it can be bulk-invalidated later.
    """
    try:
        serialized = json.dumps(data, default=str)
        _redis.setex(key, ttl, serialized)

        if user_id:
            tracking_set = _user_keys_set(user_id)
            _redis.sadd(tracking_set, key)
            # Keep tracking-set TTL at least as long as the longest tracked key.
            # Without this, writing a short-lived key after a long-lived key
            # can shrink the set TTL and make future invalidation miss keys.
            desired_ttl = ttl + 60
            current_ttl = _redis.ttl(tracking_set)
            if current_ttl in (-2, -1) or current_ttl < desired_ttl:
                _redis.expire(tracking_set, desired_ttl)

    except Exception as exc:
        logger.warning(f"[Cache] SET failed for key={key!r}: {exc}")


def invalidate_user_cache(user_id: str) -> None:
    """
    Delete every analysis cache key belonging to user_id.
    Called by the worker whenever a job finishes or fails so the
    next dashboard request gets fresh aggregated data.
    """
    try:
        tracking_set = _user_keys_set(user_id)
        keys = _redis.smembers(tracking_set)
        if keys:
            _redis.delete(*keys)
            logger.info(f"[Cache] Invalidated {len(keys)} key(s) for user {user_id}")
        _redis.delete(tracking_set)
    except Exception as exc:
        logger.warning(f"[Cache] Invalidation failed for user {user_id}: {exc}")


def invalidate_job_summary_cache(job_id: str) -> None:
    """
    Delete the per-job summary cache key directly.
    This is a safety net for mutation paths where we need immediate freshness.
    """
    key = f"analysis:job_summary:{job_id}"
    try:
        _redis.delete(key)
    except Exception as exc:
        logger.warning(f"[Cache] Job summary invalidation failed for {job_id}: {exc}")
