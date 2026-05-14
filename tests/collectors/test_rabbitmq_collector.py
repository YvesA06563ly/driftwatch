"""Tests for the RabbitMQ collector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.rabbitmq_collector import RabbitMQCollector


def _make_collector(extra: dict | None = None) -> RabbitMQCollector:
    cfg = {"url": "http://rabbit:15672", "username": "admin", "password": "secret"}
    if extra:
        cfg.update(extra)
    return RabbitMQCollector(cfg)


def _make_response(data: list) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture()
def patched_get():
    with patch("driftwatch.collectors.rabbitmq_collector.requests.get") as mock_get:
        yield mock_get


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_config_ok():
    _make_collector().validate_config()  # should not raise


def test_validate_config_empty_url_raises():
    with pytest.raises(ValueError, match="non-empty 'url'"):
        RabbitMQCollector({"url": ""}).validate_config()


def test_validate_config_bad_resource_raises():
    with pytest.raises(ValueError, match="unknown resource"):
        _make_collector({"resources": ["topics"]}).validate_config()


def test_validate_config_bad_pattern_raises():
    with pytest.raises(ValueError, match="invalid name_pattern"):
        _make_collector({"name_pattern": "[invalid"}).validate_config()


# ---------------------------------------------------------------------------
# collect – queues
# ---------------------------------------------------------------------------

def test_collect_queues_returns_snapshot(patched_get):
    queue = {"name": "jobs", "messages": 42, "consumers": 3, "state": "running", "durable": True}
    patched_get.return_value = _make_response([queue])
    c = _make_collector({"resources": ["queues"]})
    snap = c.collect()
    assert "queues/jobs" in snap.data
    assert snap.data["queues/jobs"]["messages"] == 42
    assert snap.data["queues/jobs"]["consumers"] == 3


def test_collect_exchanges_returns_snapshot(patched_get):
    exchange = {"name": "logs", "type": "fanout", "durable": True, "auto_delete": False}
    patched_get.return_value = _make_response([exchange])
    c = _make_collector({"resources": ["exchanges"]})
    snap = c.collect()
    assert "exchanges/logs" in snap.data
    assert snap.data["exchanges/logs"]["type"] == "fanout"


def test_collect_with_name_pattern_filters(patched_get):
    queues = [
        {"name": "jobs.high", "messages": 1, "consumers": 1, "state": "running", "durable": True},
        {"name": "dead.letter", "messages": 0, "consumers": 0, "state": "idle", "durable": False},
    ]
    patched_get.return_value = _make_response(queues)
    c = _make_collector({"resources": ["queues"], "name_pattern": r"^jobs"})
    snap = c.collect()
    assert "queues/jobs.high" in snap.data
    assert "queues/dead.letter" not in snap.data


def test_collect_snapshot_source_is_rabbitmq(patched_get):
    patched_get.return_value = _make_response([])
    c = _make_collector()
    snap = c.collect()
    assert snap.source == "rabbitmq"


def test_collect_empty_response_returns_empty_data(patched_get):
    patched_get.return_value = _make_response([])
    c = _make_collector({"resources": ["queues"]})
    snap = c.collect()
    assert snap.data == {}
