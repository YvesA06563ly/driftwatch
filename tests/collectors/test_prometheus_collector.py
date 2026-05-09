"""Tests for PrometheusCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.prometheus_collector import PrometheusCollector

_EXPOSITION = """\
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="get"} 1027
http_requests_total{method="post"} 3
process_resident_memory_bytes 2.2e+07
go_goroutines 8
"""


def _make_response(text: str, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


@pytest.fixture()
def collector():
    return PrometheusCollector({"urls": ["http://localhost:9090/metrics"]})


def test_validate_config_ok(collector):
    collector.validate_config()  # should not raise


def test_validate_config_empty_urls_raises():
    with pytest.raises(ValueError, match="at least one url"):
        PrometheusCollector({"urls": []}).validate_config()


def test_validate_config_bad_url_raises():
    with pytest.raises(ValueError, match="invalid prometheus url"):
        PrometheusCollector({"urls": ["ftp://bad"]}).validate_config()


def test_validate_config_bad_pattern_raises():
    with pytest.raises(ValueError, match="invalid metric_pattern"):
        PrometheusCollector(
            {"urls": ["http://localhost:9090/metrics"], "metric_pattern": "[unclosed"}
        ).validate_config()


def test_collect_returns_all_metrics(collector):
    with patch("driftwatch.collectors.prometheus_collector.requests.get") as mock_get:
        mock_get.return_value = _make_response(_EXPOSITION)
        snap = collector.collect()
    url_data = snap.data["http://localhost:9090/metrics"]
    assert 'http_requests_total{method="get"}' in url_data
    assert url_data['http_requests_total{method="get"}'] == "1027"
    assert "go_goroutines" in url_data


def test_collect_with_metric_pattern():
    c = PrometheusCollector(
        {"urls": ["http://localhost:9090/metrics"], "metric_pattern": "^go_"}
    )
    with patch("driftwatch.collectors.prometheus_collector.requests.get") as mock_get:
        mock_get.return_value = _make_response(_EXPOSITION)
        snap = c.collect()
    url_data = snap.data["http://localhost:9090/metrics"]
    assert "go_goroutines" in url_data
    assert "process_resident_memory_bytes" not in url_data


def test_collect_http_error_records_error():
    c = PrometheusCollector({"urls": ["http://localhost:9090/metrics"]})
    with patch("driftwatch.collectors.prometheus_collector.requests.get") as mock_get:
        mock_get.return_value = _make_response("", status=503)
        snap = c.collect()
    assert "error" in snap.data["http://localhost:9090/metrics"]


def test_collect_multiple_urls():
    urls = ["http://host1:9090/metrics", "http://host2:9090/metrics"]
    c = PrometheusCollector({"urls": urls})
    with patch("driftwatch.collectors.prometheus_collector.requests.get") as mock_get:
        mock_get.return_value = _make_response(_EXPOSITION)
        snap = c.collect()
    assert set(snap.data.keys()) == set(urls)


def test_collect_snapshot_collector_name(collector):
    with patch("driftwatch.collectors.prometheus_collector.requests.get") as mock_get:
        mock_get.return_value = _make_response(_EXPOSITION)
        snap = collector.collect()
    assert snap.collector == "prometheus"
