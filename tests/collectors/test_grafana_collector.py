"""Tests for GrafanaCollector."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.grafana_collector import GrafanaCollector


BASE_CONFIG = {
    "url": "https://grafana.example.com",
    "api_key": "glsa_secret",
    "resources": ["dashboards", "datasources"],
}

DASHBOARDS = [
    {"uid": "abc123", "title": "Infra Overview", "version": 5, "folderTitle": "Ops"},
    {"uid": "xyz789", "title": "App Metrics", "version": 2, "folderTitle": ""},
]

DATASOURCES = [
    {"name": "Prometheus", "type": "prometheus", "url": "http://prom:9090", "access": "proxy", "isDefault": True},
    {"name": "Loki", "type": "loki", "url": "http://loki:3100", "access": "proxy", "isDefault": False},
]


def _make_response(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    return r


@pytest.fixture()
def patched_session():
    with patch("driftwatch.collectors.grafana_collector.requests.Session") as mock_cls:
        session = MagicMock()
        mock_cls.return_value = session
        session.get.side_effect = [
            _make_response(DASHBOARDS),
            _make_response(DATASOURCES),
        ]
        yield session


def test_validate_config_ok():
    c = GrafanaCollector(BASE_CONFIG)
    c.validate_config()  # should not raise


def test_validate_config_empty_url_raises():
    with pytest.raises(ValueError, match="non-empty 'url'"):
        GrafanaCollector({**BASE_CONFIG, "url": ""}).validate_config()


def test_validate_config_bad_url_raises():
    with pytest.raises(ValueError, match="http"):
        GrafanaCollector({**BASE_CONFIG, "url": "ftp://bad"}).validate_config()


def test_validate_config_empty_api_key_raises():
    with pytest.raises(ValueError, match="api_key"):
        GrafanaCollector({**BASE_CONFIG, "api_key": ""}).validate_config()


def test_validate_config_unknown_resource_raises():
    with pytest.raises(ValueError, match="unknown grafana resources"):
        GrafanaCollector({**BASE_CONFIG, "resources": ["alerts"]}).validate_config()


def test_validate_config_empty_resources_raises():
    with pytest.raises(ValueError, match="at least one resource"):
        GrafanaCollector({**BASE_CONFIG, "resources": []}).validate_config()


def test_collect_returns_all_dashboards_and_datasources(patched_session):
    c = GrafanaCollector(BASE_CONFIG)
    snap = c.collect()
    assert "dashboard:abc123" in snap.data
    assert "dashboard:xyz789" in snap.data
    assert "datasource:Prometheus" in snap.data
    assert "datasource:Loki" in snap.data


def test_collect_dashboard_fields(patched_session):
    c = GrafanaCollector(BASE_CONFIG)
    snap = c.collect()
    entry = snap.data["dashboard:abc123"]
    assert entry["title"] == "Infra Overview"
    assert entry["version"] == 5
    assert entry["folderTitle"] == "Ops"


def test_collect_with_pattern_filters(patched_session):
    patched_session.get.side_effect = [
        _make_response(DASHBOARDS),
        _make_response(DATASOURCES),
    ]
    c = GrafanaCollector({**BASE_CONFIG, "pattern": "Infra"})
    snap = c.collect()
    assert "dashboard:abc123" in snap.data
    assert "dashboard:xyz789" not in snap.data
    assert "datasource:Prometheus" not in snap.data


def test_collect_only_datasources():
    with patch("driftwatch.collectors.grafana_collector.requests.Session") as mock_cls:
        session = MagicMock()
        mock_cls.return_value = session
        session.get.return_value = _make_response(DATASOURCES)
        c = GrafanaCollector({**BASE_CONFIG, "resources": ["datasources"]})
        snap = c.collect()
        assert all(k.startswith("datasource:") for k in snap.data)
        assert session.get.call_count == 1
