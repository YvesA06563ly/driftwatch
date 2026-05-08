"""Tests for EtcdCollector."""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.etcd_collector import EtcdCollector


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def _make_response(kvs: list[tuple[str, str]]) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "kvs": [{"key": _b64(k), "value": _b64(v)} for k, v in kvs]
    }
    return mock


@pytest.fixture()
def collector() -> EtcdCollector:
    return EtcdCollector({"url": "http://localhost:2379"})


def test_validate_config_ok(collector: EtcdCollector) -> None:
    collector.validate_config()  # should not raise


def test_validate_config_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="non-empty 'url'"):
        EtcdCollector({"url": ""}).validate_config()


def test_validate_config_bad_pattern_raises() -> None:
    with pytest.raises(ValueError, match="pattern"):
        EtcdCollector({"url": "http://localhost:2379", "pattern": "[invalid"}).validate_config()


def test_collect_returns_all_keys(collector: EtcdCollector) -> None:
    kvs = [("/app/host", "localhost"), ("/app/port", "8080")]
    with patch("requests.post", return_value=_make_response(kvs)) as mock_post:
        snap = collector.collect()

    assert snap.source == "etcd"
    assert snap.data["/app/host"] == "localhost"
    assert snap.data["/app/port"] == "8080"
    mock_post.assert_called_once()


def test_collect_with_pattern_filters_keys() -> None:
    col = EtcdCollector({"url": "http://localhost:2379", "pattern": r"/app/port"})
    kvs = [("/app/host", "localhost"), ("/app/port", "8080")]
    with patch("requests.post", return_value=_make_response(kvs)):
        snap = col.collect()

    assert "/app/port" in snap.data
    assert "/app/host" not in snap.data


def test_collect_empty_response_returns_empty_dict(collector: EtcdCollector) -> None:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {}
    with patch("requests.post", return_value=mock):
        snap = collector.collect()

    assert snap.data == {}


def test_collect_uses_correct_endpoint(collector: EtcdCollector) -> None:
    with patch("requests.post", return_value=_make_response([])) as mock_post:
        collector.collect()

    url_called = mock_post.call_args[0][0]
    assert url_called == "http://localhost:2379/v3/kv/range"


def test_collect_respects_timeout() -> None:
    col = EtcdCollector({"url": "http://localhost:2379", "timeout": 10})
    with patch("requests.post", return_value=_make_response([])) as mock_post:
        col.collect()

    assert mock_post.call_args[1]["timeout"] == 10


def test_collect_http_error_propagates(collector: EtcdCollector) -> None:
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("connection refused")
    with patch("requests.post", return_value=mock):
        with pytest.raises(Exception, match="connection refused"):
            collector.collect()
