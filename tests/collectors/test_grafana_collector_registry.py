"""Registry integration tests for GrafanaCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors

BASE_CONFIG = {
    "url": "https://grafana.example.com",
    "api_key": "glsa_secret",
}

DATASOURCES = [
    {"name": "Prometheus", "type": "prometheus", "url": "http://prom:9090", "access": "proxy", "isDefault": True},
]


def _make_response(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    return r


def test_grafana_in_list_collectors():
    assert "grafana" in list_collectors()


def test_get_collector_returns_grafana_instance():
    from driftwatch.collectors.grafana_collector import GrafanaCollector
    c = get_collector("grafana", BASE_CONFIG)
    assert isinstance(c, GrafanaCollector)


def test_get_collector_grafana_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("grafana", {"url": "", "api_key": "x"})


def test_get_collector_grafana_collect_via_registry():
    with patch("driftwatch.collectors.grafana_collector.requests.Session") as mock_cls:
        session = MagicMock()
        mock_cls.return_value = session
        session.get.return_value = _make_response(DATASOURCES)
        c = get_collector("grafana", {**BASE_CONFIG, "resources": ["datasources"]})
        snap = c.collect()
        assert snap.source == "grafana"
        assert any(k.startswith("datasource:") for k in snap.data)
