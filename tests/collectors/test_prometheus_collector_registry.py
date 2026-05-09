"""Integration tests: PrometheusCollector wired into the collector registry."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors

_EXPOSITION = "go_goroutines 8\nprocess_cpu_seconds_total 0.12\n"


def _make_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def test_prometheus_in_list_collectors():
    assert "prometheus" in list_collectors()


def test_get_collector_returns_prometheus_instance():
    from driftwatch.collectors.prometheus_collector import PrometheusCollector

    c = get_collector("prometheus", {"urls": ["http://localhost:9090/metrics"]})
    assert isinstance(c, PrometheusCollector)


def test_get_collector_prometheus_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("prometheus", {"urls": []})


def test_get_collector_prometheus_collect_via_registry():
    c = get_collector("prometheus", {"urls": ["http://localhost:9090/metrics"]})
    with patch("driftwatch.collectors.prometheus_collector.requests.get") as mock_get:
        mock_get.return_value = _make_response(_EXPOSITION)
        snap = c.collect()
    assert "go_goroutines" in snap.data["http://localhost:9090/metrics"]
