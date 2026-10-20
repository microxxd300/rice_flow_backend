import functools
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)
_MISSING = object()


def cached(key: str, ttl: int, fetch):
    """Return (value, hit). Only successful fetches are stored, so errors are never cached.

    If the cache itself is unreachable (e.g. Redis is down), fall back to fetching directly.
    """
    try:
        value = cache.get(key, _MISSING)
    except Exception:
        logger.warning('cache unavailable, fetching %s directly', key)
        return fetch(), False
    if value is not _MISSING:
        logger.info('cache HIT %s', key)
        return value, True

    value = fetch()
    try:
        cache.set(key, value, ttl)
    except Exception:
        logger.warning('cache unavailable, could not store %s', key)
    logger.info('cache MISS %s', key)
    return value, False


def location_key(prefix: str, lat: float, lon: float, places: int = 4) -> str:
    # 4 decimal places is about 11 m, so rescans of the same farm share a key
    return f'{prefix}:{round(lat, places)}:{round(lon, places)}'


def cached_by_location(prefix: str, ttl: int):
    """Cache a fn(lat, lon) result per location. The data is not user-specific."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(lat: float, lon: float):
            return cached(location_key(prefix, lat, lon), ttl, lambda: fn(lat, lon))[0]
        return wrapper
    return decorator
