"""Tests for RedisCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.redis_collector import RedisCollector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_collector(extra: dict | None = None) -> RedisCollector:
    cfg: dict = {"url": "redis://localhost:6379/0"}
    if extra:
        cfg.update(extra)
    return RedisCollector(cfg)


def _fake_client(config_data: dict, info_data: dict) -> MagicMock:
    client = MagicMock()
    client.config_get.return_value = config_data
    client.info.side_effect = lambda section: info_data.get(section, {})
    return client


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_empty_url_raises() -> None:
    c = RedisCollector({"url": ""})
    with pytest.raises(ValueError, match="non-empty 'url'"):
        c.validate_config()


def test_validate_ok_does_not_raise() -> None:
    with patch("driftwatch.collectors.redis_collector.redis_lib", MagicMock()):
        c = _make_collector()
        c.validate_config()  # should not raise


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

@pytest.fixture()
def patched_redis():
    """Patch redis.from_url to return a controllable fake client."""
    fake = _fake_client(
        config_data={"maxmemory": "0", "hz": "10"},
        info_data={"server": {"redis_version": "7.0.0", "os": "Linux"}},
    )
    with patch("driftwatch.collectors.redis_collector.redis_lib") as mock_lib:
        mock_lib.from_url.return_value = fake
        yield fake


def test_collect_config_keys_prefixed(patched_redis: MagicMock) -> None:
    snap = _make_collector().collect()
    assert "config:maxmemory" in snap.data
    assert snap.data["config:hz"] == "10"


def test_collect_info_keys_prefixed(patched_redis: MagicMock) -> None:
    snap = _make_collector().collect()
    assert "info:server:redis_version" in snap.data
    assert snap.data["info:server:redis_version"] == "7.0.0"


def test_collect_source_is_redis(patched_redis: MagicMock) -> None:
    snap = _make_collector().collect()
    assert snap.source == "redis"


def test_collect_exclude_pattern_removes_keys(patched_redis: MagicMock) -> None:
    snap = _make_collector({"exclude_pattern": r"^info:"}).collect()
    assert all(not k.startswith("info:") for k in snap.data)
    assert "config:maxmemory" in snap.data


def test_collect_multiple_info_sections() -> None:
    fake = _fake_client(
        config_data={},
        info_data={
            "server": {"redis_version": "7.0.0"},
            "replication": {"role": "master"},
        },
    )
    with patch("driftwatch.collectors.redis_collector.redis_lib") as mock_lib:
        mock_lib.from_url.return_value = fake
        snap = _make_collector({"info_sections": ["server", "replication"]}).collect()
    assert snap.data["info:replication:role"] == "master"
    assert snap.data["info:server:redis_version"] == "7.0.0"


def test_collect_config_pattern_forwarded(patched_redis: MagicMock) -> None:
    _make_collector({"config_pattern": "max*"}).collect()
    patched_redis.config_get.assert_called_once_with("max*")
