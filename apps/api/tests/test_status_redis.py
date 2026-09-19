from types import SimpleNamespace

from pydantic import SecretStr
from pytest import MonkeyPatch
from redis.exceptions import ConnectionError

from oceanscope_api.status import redis as redis_status


class StubRedis:
    def __init__(self, *, available: bool) -> None:
        self.available = available
        self.closed = False

    def ping(self) -> bool:
        if not self.available:
            raise ConnectionError("TEST DATA Redis unavailable")
        return True

    def close(self) -> None:
        self.closed = True


def test_unconfigured_redis_is_offline(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        redis_status,
        "get_settings",
        lambda: SimpleNamespace(redis_url=None),
    )

    assert redis_status.redis_is_available() is False


def test_redis_probe_reports_ping_and_closes_client(monkeypatch: MonkeyPatch) -> None:
    client = StubRedis(available=True)
    monkeypatch.setattr(
        redis_status,
        "get_settings",
        lambda: SimpleNamespace(redis_url=SecretStr("redis://example.test:6379/0")),
    )
    monkeypatch.setattr(
        redis_status.Redis,
        "from_url",
        lambda *_args, **_kwargs: client,
    )

    assert redis_status.redis_is_available() is True
    assert client.closed is True


def test_redis_probe_reports_connection_failure_without_raising(
    monkeypatch: MonkeyPatch,
) -> None:
    client = StubRedis(available=False)
    monkeypatch.setattr(
        redis_status,
        "get_settings",
        lambda: SimpleNamespace(redis_url=SecretStr("redis://example.test:6379/0")),
    )
    monkeypatch.setattr(
        redis_status.Redis,
        "from_url",
        lambda *_args, **_kwargs: client,
    )

    assert redis_status.redis_is_available() is False
    assert client.closed is True


def test_redis_probe_reports_invalid_url_without_raising(monkeypatch: MonkeyPatch) -> None:
    def invalid_url(*_args: object, **_kwargs: object) -> StubRedis:
        raise ValueError("TEST DATA invalid URL")

    monkeypatch.setattr(
        redis_status,
        "get_settings",
        lambda: SimpleNamespace(redis_url=SecretStr("not-a-redis-url")),
    )
    monkeypatch.setattr(
        redis_status.Redis,
        "from_url",
        invalid_url,
    )

    assert redis_status.redis_is_available() is False
