"""Registry integration tests for HaproxyCollector."""
from __future__ import annotations

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors

_CSV = textwrap.dedent("""\
    # pxname,svname,status,scur,smax,ereq,econ,eresp
    frontend_http,FRONTEND,OPEN,5,50,0,0,0
""")


def _make_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def test_haproxy_in_list_collectors():
    assert "haproxy" in list_collectors()


def test_get_collector_returns_haproxy_instance():
    from driftwatch.collectors.haproxy_collector import HaproxyCollector

    instance = get_collector("haproxy", {"url": "http://localhost:8404/stats;csv"})
    assert isinstance(instance, HaproxyCollector)


def test_get_collector_haproxy_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("haproxy", {})


@patch("driftwatch.collectors.haproxy_collector.requests.get")
def test_get_collector_haproxy_collect_via_registry(mock_get):
    mock_get.return_value = _make_response(_CSV)
    collector = get_collector("haproxy", {"url": "http://localhost:8404/stats;csv"})
    snap = collector.collect()
    assert snap.source == "haproxy"
    assert "frontend_http/FRONTEND" in snap.data
