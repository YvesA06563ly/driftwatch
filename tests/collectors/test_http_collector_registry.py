"""Integration-level tests: HttpCollector wired through the collector registry."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors


def test_http_in_list_collectors():
    assert "http" in list_collectors()


def test_get_collector_returns_http_instance():
    from driftwatch.collectors.http_collector import HttpCollector

    col = get_collector("http", "probe", {"urls": ["http://example.com"]})
    assert isinstance(col, HttpCollector)


def test_get_collector_http_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("http", "probe", {"urls": []})


def test_get_collector_http_collect_via_registry():
    resp_mock = MagicMock(status_code=200, headers={})
    col = get_collector("http", "probe", {"urls": ["http://example.com"]})
    with patch(
        "driftwatch.collectors.http_collector.requests.request",
        return_value=resp_mock,
    ):
        snap = col.collect()
    assert snap.data["http://example.com"]["status_code"] == 200
