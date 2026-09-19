from __future__ import annotations

from contextlib import suppress

from redis import Redis
from redis.exceptions import RedisError

from oceanscope_api.core.settings import get_settings


def redis_is_available() -> bool:
    redis_url = get_settings().redis_url
    if redis_url is None:
        return False

    try:
        client = Redis.from_url(
            redis_url.get_secret_value(),
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
    except (RedisError, ValueError):
        return False
    try:
        return bool(client.ping())
    except RedisError:
        return False
    finally:
        with suppress(RedisError):
            client.close()
