"""Tests for PostgresCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.postgres_collector import PostgresCollector


def _make_collector(extra: dict | None = None) -> PostgresCollector:
    cfg = {"dsn": "postgresql://user:pass@localhost/mydb"}
    if extra:
        cfg.update(extra)
    return PostgresCollector(cfg)


def _make_cursor(rows: list[dict]) -> MagicMock:
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.return_value = rows
    return cur


@pytest.fixture()
def patched_psycopg2():
    mock_conn = MagicMock()
    with patch("driftwatch.collectors.postgres_collector.psycopg2") as mock_pg:
        mock_pg.connect.return_value = mock_conn
        mock_pg.extras = MagicMock()
        yield mock_pg, mock_conn


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_config_ok():
    _make_collector().validate_config()  # no exception


def test_validate_config_empty_dsn_raises():
    with pytest.raises(ValueError, match="dsn"):
        PostgresCollector({"dsn": ""}).validate_config()


def test_validate_config_missing_dsn_raises():
    with pytest.raises(ValueError, match="dsn"):
        PostgresCollector({}).validate_config()


def test_validate_config_bad_pattern_raises():
    with pytest.raises(ValueError, match="param_pattern"):
        PostgresCollector({"dsn": "x", "param_pattern": "[invalid"}).validate_config()


# ---------------------------------------------------------------------------
# collect — settings
# ---------------------------------------------------------------------------

def test_collect_returns_settings(patched_psycopg2):
    mock_pg, mock_conn = patched_psycopg2
    setting_rows = [
        {"name": "max_connections", "setting": "100"},
        {"name": "work_mem", "setting": "4096"},
    ]
    cur = _make_cursor(setting_rows)
    mock_conn.cursor.return_value = cur

    snap = _make_collector().collect()

    assert snap.data["setting:max_connections"] == "100"
    assert snap.data["setting:work_mem"] == "4096"
    assert snap.source == "postgres"


def test_collect_with_param_pattern_uses_regex_query(patched_psycopg2):
    mock_pg, mock_conn = patched_psycopg2
    cur = _make_cursor([{"name": "wal_level", "setting": "replica"}])
    mock_conn.cursor.return_value = cur

    snap = _make_collector({"param_pattern": "^wal_"}).collect()

    assert "setting:wal_level" in snap.data
    call_sql = cur.execute.call_args[0][0]
    assert "~" in call_sql  # regex operator used


def test_collect_closes_connection_on_success(patched_psycopg2):
    mock_pg, mock_conn = patched_psycopg2
    mock_conn.cursor.return_value = _make_cursor([])

    _make_collector().collect()

    mock_conn.close.assert_called_once()


def test_collect_closes_connection_on_error(patched_psycopg2):
    mock_pg, mock_conn = patched_psycopg2
    mock_conn.cursor.side_effect = RuntimeError("db error")

    with pytest.raises(RuntimeError):
        _make_collector().collect()

    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# collect — replication slots
# ---------------------------------------------------------------------------

def test_collect_includes_replication_slots(patched_psycopg2):
    mock_pg, mock_conn = patched_psycopg2
    setting_rows = [{"name": "wal_level", "setting": "replica"}]
    slot_rows = [
        {"slot_name": "slot1", "slot_type": "physical", "active": True, "restart_lsn": "0/3000000"},
    ]
    cur = _make_cursor([])
    cur.fetchall.side_effect = [setting_rows, slot_rows]
    mock_conn.cursor.return_value = cur

    snap = _make_collector({"include_replication": True}).collect()

    assert snap.data["replication_slot:slot1:type"] == "physical"
    assert snap.data["replication_slot:slot1:active"] == "True"
    assert snap.data["replication_slot:slot1:restart_lsn"] == "0/3000000"
