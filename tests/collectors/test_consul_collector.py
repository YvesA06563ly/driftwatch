"""Tests for ConsulCollector."""
from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.consul_collector import ConsulCollector


def _make_entry(key: str, value: str) -> dict:
    encoded = base64.b64encode(value.encode()).decode()
    return {"Key": key, "Value": encoded, "Flags": 0}


def _make_response(entries: list[dict], status: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = entries
    mock.raise_for_status = MagicMock(
        side_effect=None if status < 400 else Exception(f"HTTP {status}")
    )
    return mock


@pytest.fixture()
def collector():
    return ConsulCollector({"url": "http://consul:8500", "prefix": "config/"})


def test_validate_config_ok():
    c = ConsulCollector({"url": "http://localhost:8500", "prefix": "app"})
    c.validate_config()  # should not raise


def test_validate_config_bad_url_raises():
    c = ConsulCollector({"url": "ftp://bad"})
    with pytest.raises(ValueError, match="http"):
        c.validate_config()


def test_validate_config_bad_pattern_raises():
    c = ConsulCollector({"url": "http://localhost:8500", "pattern": "[invalid"})
    with pytest.raises(ValueError, match="pattern"):
        c.validate_config()


def test_collect_returns_all_keys(collector):
    entries = [
        _make_entry("config/db/host", "localhost"),
        _make_entry("config/db/port", "5432"),
    ]
    with patch("requests.get", return_value=_make_response(entries)):
        snap = collector.collect()
    assert snap.data["config/db/host"] == "localhost"
    assert snap.data["config/db/port"] == "5432"


def test_collect_with_pattern_filters_keys():
    c = ConsulCollector({"url": "http://consul:8500", "pattern": r"db/"})
    entries = [
        _make_entry("config/db/host", "localhost"),
        _make_entry("config/cache/host", "redis"),
    ]
    with patch("requests.get", return_value=_make_response(entries)):
        snap = c.collect()
    assert "config/db/host" in snap.data
    assert "config/cache/host" not in snap.data


def test_collect_empty_value_key():
    entries = [{"Key": "config/empty", "Value": None, "Flags": 0}]
    c = ConsulCollector({"url": "http://consul:8500"})
    with patch("requests.get", return_value=_make_response(entries)):
        snap = c.collect()
    assert snap.data["config/empty"] == ""


def test_collect_request_error_returns_error_snapshot(collector):
    import requests as req

    with patch("requests.get", side_effect=req.ConnectionError("refused")):
        snap = collector.collect()
    assert "error" in snap.data
    assert "refused" in snap.data["error"]


def test_token_sent_as_header():
    c = ConsulCollector({"url": "http://consul:8500", "token": "secret-token"})
    entries = [_make_entry("k", "v")]
    with patch("requests.get", return_value=_make_response(entries)) as mock_get:
        c.collect()
    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["X-Consul-Token"] == "secret-token"
