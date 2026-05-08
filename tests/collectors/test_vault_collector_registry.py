"""Registry integration tests for VaultCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors


BASE_CFG = {
    "url": "http://vault:8200",
    "token": "s.abc",
    "paths": ["svc/config"],
}


def _make_meta_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": {
            "current_version": 2,
            "created_time": "2024-01-01T00:00:00Z",
            "updated_time": "2024-05-01T00:00:00Z",
        }
    }
    resp.raise_for_status = MagicMock()
    return resp


def test_vault_in_list_collectors():
    assert "vault" in list_collectors()


def test_get_collector_returns_vault_instance():
    from driftwatch.collectors.vault_collector import VaultCollector
    c = get_collector("vault", BASE_CFG)
    assert isinstance(c, VaultCollector)


def test_get_collector_vault_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("vault", {"url": "http://vault:8200", "token": "", "paths": ["x"]})


def test_get_collector_vault_collect_via_registry():
    c = get_collector("vault", BASE_CFG)
    with patch("requests.get", return_value=_make_meta_response()):
        snap = c.collect()
    assert "svc/config" in snap.data
    assert snap.data["svc/config"]["version"] == 2
