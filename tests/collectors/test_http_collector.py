"""Tests for HttpCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from driftwatch.collectors.http_collector import HttpCollector


BASE_CFG = {"urls": ["http://example.com"], "timeout": 2.0}


def _make_response(status: int = 200, headers: dict | None = None, elapsed: float = 0.1):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = headers or {}
    return resp, elapsed


@pytest.fixture()
def collector():
    return HttpCollector("http_test", BASE_CFG)


def test_validate_config_ok(collector):
    collector.validate_config()  # should not raise


def test_validate_config_empty_urls_raises():
    with pytest.raises(ValueError, match="non-empty"):
        HttpCollector("x", {"urls": []}).validate_config()


def test_validate_config_bad_url_raises():
    with pytest.raises(ValueError, match="invalid url"):
        HttpCollector("x", {"urls": ["ftp://bad"]}).validate_config()


def test_validate_config_bad_timeout_raises():
    with pytest.raises(ValueError, match="positive"):
        HttpCollector("x", {"urls": ["http://x.com"], "timeout": -1}).validate_config()


def test_collect_reachable_endpoint():
    resp_mock = MagicMock()
    resp_mock.status_code = 200
    resp_mock.headers = {"content-type": "application/json"}

    cfg = {"urls": ["http://example.com"], "capture_headers": ["content-type"]}
    col = HttpCollector("h", cfg)

    with patch("driftwatch.collectors.http_collector.requests.request", return_value=resp_mock):
        snap = col.collect()

    entry = snap.data["http://example.com"]
    assert entry["status_code"] == 200
    assert entry["reachable"] is True
    assert entry["header:content-type"] == "application/json"
    assert "elapsed_ms" in entry


def test_collect_unreachable_endpoint():
    col = HttpCollector("h", BASE_CFG)
    with patch(
        "driftwatch.collectors.http_collector.requests.request",
        side_effect=requests.ConnectionError("refused"),
    ):
        snap = col.collect()

    entry = snap.data["http://example.com"]
    assert entry["reachable"] is False
    assert entry["error"] == "ConnectionError"


def test_collect_multiple_urls():
    resp_mock = MagicMock(status_code=200, headers={})
    cfg = {"urls": ["http://a.com", "http://b.com"]}
    col = HttpCollector("h", cfg)
    with patch("driftwatch.collectors.http_collector.requests.request", return_value=resp_mock):
        snap = col.collect()

    assert "http://a.com" in snap.data
    assert "http://b.com" in snap.data


def test_snapshot_collector_name():
    resp_mock = MagicMock(status_code=204, headers={})
    col = HttpCollector("my_http", BASE_CFG)
    with patch("driftwatch.collectors.http_collector.requests.request", return_value=resp_mock):
        snap = col.collect()
    assert snap.collector == "my_http"
