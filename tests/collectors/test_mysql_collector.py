"""Tests for MySQLCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.mysql_collector import MySQLCollector


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

VARIABLES_ROWS = [
    ("max_connections", "151"),
    ("innodb_buffer_pool_size", "134217728"),
    ("wait_timeout", "28800"),
]

STATUS_ROWS = [
    ("Threads_connected", "3"),
    ("Queries", "10042"),
]


def _make_collector(extra: dict | None = None) -> MySQLCollector:
    cfg = {"dsn": "mysql://root:secret@127.0.0.1:3306/mydb", **(extra or {})}
    return MySQLCollector(cfg)


def _fake_connect(variables_rows=VARIABLES_ROWS, status_rows=STATUS_ROWS):
    """Return a patched pymysql.connect context."""
    cursor = MagicMock()
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.side_effect = [variables_rows, status_rows]

    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.close = MagicMock()

    return patch("driftwatch.collectors.mysql_collector.pymysql.connect", return_value=conn), conn, cursor


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_empty_dsn_raises():
    with pytest.raises(ValueError, match="non-empty 'dsn'"):
        MySQLCollector({"dsn": "", "variables": ["max_connections"]}).validate_config()


def test_validate_no_targets_raises():
    with pytest.raises(ValueError, match="at least one of"):
        MySQLCollector({"dsn": "mysql://host/db"}).validate_config()


def test_validate_bad_pattern_raises():
    with pytest.raises(ValueError, match="Invalid 'pattern'"):
        MySQLCollector({"dsn": "mysql://host/db", "pattern": "[unclosed"}).validate_config()


def test_validate_ok_with_variables():
    _make_collector({"variables": ["max_connections"]}).validate_config()  # no raise


def test_validate_ok_with_pattern():
    _make_collector({"pattern": "^innodb_"}).validate_config()  # no raise


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def test_collect_explicit_variables():
    patcher, conn, cursor = _fake_connect()
    cursor.fetchall.side_effect = [VARIABLES_ROWS]
    with patcher:
        import pymysql  # noqa: F401 – ensure importable in test env
        c = _make_collector({"variables": ["max_connections", "wait_timeout"]})
        snap = c.collect()

    assert snap.source == "mysql://root:secret@127.0.0.1:3306/mydb"
    assert snap.data["variable:max_connections"] == "151"
    assert snap.data["variable:wait_timeout"] == "28800"
    assert "variable:innodb_buffer_pool_size" not in snap.data


def test_collect_status_keys():
    patcher, conn, cursor = _fake_connect()
    cursor.fetchall.side_effect = [STATUS_ROWS]
    with patcher:
        import pymysql  # noqa: F401
        c = _make_collector({"status": ["Threads_connected"]})
        snap = c.collect()

    assert snap.data["status:Threads_connected"] == "3"
    assert "status:Queries" not in snap.data


def test_collect_pattern_matches_both():
    patcher, conn, cursor = _fake_connect()
    with patcher:
        import pymysql  # noqa: F401
        c = _make_collector({"pattern": "max|Threads"})
        snap = c.collect()

    assert "variable:max_connections" in snap.data
    assert "status:Threads_connected" in snap.data
    assert "variable:wait_timeout" not in snap.data


def test_collect_connection_closed_on_error():
    conn = MagicMock()
    conn.cursor.side_effect = RuntimeError("boom")
    with patch("driftwatch.collectors.mysql_collector.pymysql.connect", return_value=conn):
        import pymysql  # noqa: F401
        c = _make_collector({"variables": ["max_connections"]})
        with pytest.raises(RuntimeError, match="boom"):
            c.collect()
    conn.close.assert_called_once()
