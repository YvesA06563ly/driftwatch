"""Integration tests: AzureCollector via the collector registry."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from driftwatch.collectors import get_collector, list_collectors


def _make_setting(key: str, value: str) -> SimpleNamespace:
    return SimpleNamespace(key=key, value=value)


def _patch_azure(monkeypatch, settings):
    mock_client_cls = MagicMock()
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.list_configuration_settings.return_value = settings

    fake_azure_app = MagicMock()
    fake_azure_app.AzureAppConfigurationClient = mock_client_cls
    fake_identity = MagicMock()

    import sys
    monkeypatch.setitem(sys.modules, "azure.appconfiguration", fake_azure_app)
    monkeypatch.setitem(sys.modules, "azure.identity", fake_identity)
    return mock_client


def test_azure_in_list_collectors():
    assert "azure" in list_collectors()


def test_get_collector_returns_azure_instance():
    from driftwatch.collectors.azure_collector import AzureCollector
    cfg = {"type": "azure", "endpoint": "https://x.azconfig.io"}
    collector = get_collector(cfg)
    assert isinstance(collector, AzureCollector)


def test_get_collector_azure_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector({"type": "azure", "endpoint": ""})


def test_get_collector_azure_collect_via_registry(monkeypatch):
    client = _patch_azure(
        monkeypatch,
        [_make_setting("feature/flag", "on")],
    )
    cfg = {"type": "azure", "endpoint": "https://x.azconfig.io"}
    collector = get_collector(cfg)
    snap = collector.collect()
    assert snap.data == {"feature/flag": "on"}
