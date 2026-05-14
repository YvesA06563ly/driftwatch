"""Tests for HaproxyCollector."""
from __future__ import annotations

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.haproxy_collector import HaproxyCollector

_CSV = textwrap.dedent("""\
    # pxname,svname,status,scur,smax,ereq,econ,eresp
    frontend_http,FRONTEND,OPEN,12,50,0,0,0
    backend_app,server1,UP,3,20,0,1,2
    backend_app,BACKEND,UP,3,20,0,1,2
    stats,FRONTEND,OPEN,0,5,0,0,0
""")


def _make_collector(extra: dict | None = None):
    cfg = {"url": "http://localhost:8404/stats;csv"}
    if extra:
        cfg.update(extra)
    return HaproxyCollector(cfg)


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_config_ok_url():
    c = HaproxyCollector({"url": "http://localhost:8404/stats;csv"})
    c.validate_config()  # should not raise


def test_validate_config_ok_socket():
    c = HaproxyCollector({"socket_path": "/run/haproxy/admin.sock"})
    c.validate_config()  # should not raise


def test_validate_config_missing_both_raises():
    with pytest.raises(ValueError, match="requires 'url' or 'socket_path'"):
        HaproxyCollector({}).validate_config()


def test_validate_config_both_raises():
    with pytest.raises(ValueError, match="specify only one"):
        HaproxyCollector({"url": "http://x", "socket_path": "/tmp/s"}).validate_config()


def test_validate_config_bad_url_raises():
    with pytest.raises(ValueError, match="must start with http"):
        HaproxyCollector({"url": "ftp://bad"}).validate_config()


def test_validate_config_bad_pattern_raises():
    with pytest.raises(ValueError, match="invalid proxy_pattern"):
        HaproxyCollector({"url": "http://x", "proxy_pattern": "[invalid"}).validate_config()


# ---------------------------------------------------------------------------
# collect via HTTP
# ---------------------------------------------------------------------------

@patch("driftwatch.collectors.haproxy_collector.requests.get")
def test_collect_returns_all_proxies(mock_get):
    mock_get.return_value = _mock_response(_CSV)
    snap = _make_collector().collect()
    assert "frontend_http/FRONTEND" in snap.data
    assert "backend_app/server1" in snap.data
    assert "stats/FRONTEND" in snap.data


@patch("driftwatch.collectors.haproxy_collector.requests.get")
def test_collect_with_proxy_pattern(mock_get):
    mock_get.return_value = _mock_response(_CSV)
    snap = _make_collector({"proxy_pattern": "^backend_"}).collect()
    assert all(k.startswith("backend_") for k in snap.data)
    assert "frontend_http/FRONTEND" not in snap.data


@patch("driftwatch.collectors.haproxy_collector.requests.get")
def test_collect_status_captured(mock_get):
    mock_get.return_value = _mock_response(_CSV)
    snap = _make_collector().collect()
    assert snap.data["backend_app/server1"]["status"] == "UP"
    assert snap.data["frontend_http/FRONTEND"]["status"] == "OPEN"


@patch("driftwatch.collectors.haproxy_collector.requests.get")
def test_collect_snapshot_source(mock_get):
    mock_get.return_value = _mock_response(_CSV)
    snap = _make_collector().collect()
    assert snap.source == "haproxy"


@patch("driftwatch.collectors.haproxy_collector.requests.get")
def test_collect_empty_csv_returns_empty_data(mock_get):
    mock_get.return_value = _mock_response("# pxname,svname,status\n")
    snap = _make_collector().collect()
    assert snap.data == {}
