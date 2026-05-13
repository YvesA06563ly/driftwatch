"""Tests for AzureCollector."""
from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.azure_collector import AzureCollector


def _make_setting(key: str, value: str) -> SimpleNamespace:
    return SimpleNamespace(key=key, value=value)


def _make_collector(extra: dict | None = None) -> AzureCollector:
    cfg = {"endpoint": "https://myapp.azconfig.io", **(extra or {})}
    return AzureCollector(cfg)


@pytest.fixture()
def patched_azure(monkeypatch):
    """Patch azure SDK so tests run without the real package."""
    mock_client_cls = MagicMock()
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client_cls.from_connection_string.return_value = mock_client

    fake_azure_app = MagicMock()
    fake_azure_app.AzureAppConfigurationClient = mock_client_cls

    fake_identity = MagicMock()

    monkeypatch.setitem(__import__("sys").modules, "azure.appconfiguration", fake_azure_app)
    monkeypatch.setitem(__import__("sys").modules, "azure.identity", fake_identity)
    return mock_client


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_config_ok():
    _make_collector()  # should not raise


def test_validate_config_empty_endpoint_raises():
    with pytest.raises(ValueError, match="non-empty 'endpoint'"):
        AzureCollector({"endpoint": ""})


def test_validate_config_missing_endpoint_raises():
    with pytest.raises(ValueError, match="non-empty 'endpoint'"):
        AzureCollector({})


def test_validate_config_bad_url_raises():
    with pytest.raises(ValueError, match="http"):
        AzureCollector({"endpoint": "ftp://bad.example.com"})


def test_validate_config_bad_pattern_raises():
    with pytest.raises(ValueError, match="key_pattern"):
        AzureCollector({"endpoint": "https://x.azconfig.io", "key_pattern": "["})


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def test_collect_returns_all_settings(patched_azure):
    patched_azure.list_configuration_settings.return_value = [
        _make_setting("app/debug", "true"),
        _make_setting("app/timeout", "30"),
    ]
    snap = _make_collector().collect()
    assert snap.data == {"app/debug": "true", "app/timeout": "30"}
    assert snap.source == "azure"


def test_collect_with_key_pattern(patched_azure):
    patched_azure.list_configuration_settings.return_value = [
        _make_setting("app/debug", "true"),
        _make_setting("db/host", "localhost"),
    ]
    snap = _make_collector({"key_pattern": r"^app/"}).collect()
    assert "app/debug" in snap.data
    assert "db/host" not in snap.data


def test_collect_passes_key_filter_to_sdk(patched_azure):
    patched_azure.list_configuration_settings.return_value = []
    _make_collector({"key_filter": "app/*"}).collect()
    call_kwargs = patched_azure.list_configuration_settings.call_args[1]
    assert call_kwargs["key_filter"] == "app/*"


def test_collect_passes_label_filter_to_sdk(patched_azure):
    patched_azure.list_configuration_settings.return_value = []
    _make_collector({"label": "production"}).collect()
    call_kwargs = patched_azure.list_configuration_settings.call_args[1]
    assert call_kwargs["label_filter"] == "production"


def test_collect_empty_result(patched_azure):
    patched_azure.list_configuration_settings.return_value = []
    snap = _make_collector().collect()
    assert snap.data == {}
