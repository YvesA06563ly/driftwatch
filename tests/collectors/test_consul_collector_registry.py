"""Verify ConsulCollector is registered in the collector registry."""
from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors


def _make_response(entries):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = entries
    mock.raise_for_status = MagicMock()
    return mock


def test_consul_in_list_collectors():
    assert "consul" in list_collectors()


def test_get_collector_returns_consul_instance():
    from driftwatch.collectors.consul_collector import ConsulCollector

    c = get_collector("consul", {"url": "http://localhost:8500"})
    assert isinstance(c, ConsulCollector)


def test_get_collector_consul_invalid_url_raises():
    with pytest.raises(ValueError):
        get_collector("consul", {"url": "ftp://bad"})


def test_get_collector_consul_collect_via_registry():
    encoded = base64.b64encode(b"bar").decode()
    entries = [{"Key": "foo", "Value": encoded, "Flags": 0}]
    c = get_collector("consul", {"url": "http://localhost:8500"})
    with patch("requests.get", return_value=_make_response(entries)):
        snap = c.collect()
    assert snap.data.get("foo") == "bar"
