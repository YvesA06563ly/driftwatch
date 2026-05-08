"""Tests for VaultCollector."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.vault_collector import VaultCollector


BASE_CFG = {
    "url": "http://vault:8200",
    "token": "s.abc123",
    "paths": ["myapp/db"],
}


def _make_meta_response(version: int = 3) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": {
            "current_version": version,
            "created_time": "2024-01-01T00:00:00Z",
            "updated_time": "2024-06-01T00:00:00Z",
        }
    }
    resp.raise_for_status = MagicMock()
    return resp


def _make_list_response(keys: list[str]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": {"keys": keys}}
    resp.raise_for_status = MagicMock()
    return resp


def _make_404() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 404
    resp.raise_for_status = MagicMock()
    return resp


def test_validate_config_ok():
    c = VaultCollector(BASE_CFG)
    c.validate_config()  # should not raise


def test_validate_config_missing_token_raises():
    cfg = {**BASE_CFG, "token": ""}
    c = VaultCollector(cfg)
    with pytest.raises(ValueError, match="token"):
        c.validate_config()


def test_validate_config_missing_paths_and_pattern_raises():
    cfg = {"url": "http://vault:8200", "token": "s.x"}
    c = VaultCollector(cfg)
    with pytest.raises(ValueError, match="paths.*pattern"):
        c.validate_config()


def test_validate_config_bad_pattern_raises():
    cfg = {**BASE_CFG, "paths": [], "pattern": "[invalid"}
    c = VaultCollector(cfg)
    with pytest.raises(ValueError, match="pattern"):
        c.validate_config()


def test_collect_existing_path():
    c = VaultCollector(BASE_CFG)
    with patch("requests.get", return_value=_make_meta_response(3)):
        snap = c.collect()
    assert snap.source == "vault"
    assert snap.data["myapp/db"]["exists"] is True
    assert snap.data["myapp/db"]["version"] == 3


def test_collect_missing_path_returns_not_exists():
    c = VaultCollector(BASE_CFG)
    with patch("requests.get", return_value=_make_404()):
        snap = c.collect()
    assert snap.data["myapp/db"] == {"exists": False}


def test_collect_with_pattern_lists_and_fetches():
    cfg = {"url": "http://vault:8200", "token": "s.x", "pattern": "^app"}
    c = VaultCollector(cfg)
    list_resp = _make_list_response(["appdb", "appredis", "other"])
    meta_resp = _make_meta_response(1)
    with patch("requests.request", return_value=list_resp), \
         patch("requests.get", return_value=meta_resp):
        snap = c.collect()
    assert "appdb" in snap.data
    assert "appredis" in snap.data
    assert "other" not in snap.data


def test_collect_pattern_list_404_returns_empty():
    cfg = {"url": "http://vault:8200", "token": "s.x", "pattern": ".*"}
    c = VaultCollector(cfg)
    with patch("requests.request", return_value=_make_404()):
        snap = c.collect()
    assert snap.data == {}
