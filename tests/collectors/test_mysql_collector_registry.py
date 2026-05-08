"""Registry integration tests for MySQLCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors

VARIABLES_ROWS = [("max_connections", "151")]
STATUS_ROWS: list = []


def test_mysql_in_list_collectors():
    assert "mysql" in list_collectors()


def test_get_collector_returns_mysql_instance():
    from driftwatch.collectors.mysql_collector import MySQLCollector

    cfg = {"dsn": "mysql://root@127.0.0.1/db", "variables": ["max_connections"]}
    inst = get_collector("mysql", cfg)
    assert isinstance(inst, MySQLCollector)


def test_get_collector_mysql_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("mysql", {"dsn": "", "variables": ["x"]})


def test_get_collector_mysql_collect_via_registry():
    cursor = MagicMock()
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchall.side_effect = [VARIABLES_ROWS]

    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.close = MagicMock()

    cfg = {"dsn": "mysql://root@127.0.0.1/db", "variables": ["max_connections"]}
    with patch("driftwatch.collectors.mysql_collector.pymysql.connect", return_value=conn):
        import pymysql  # noqa: F401
        inst = get_collector("mysql", cfg)
        snap = inst.collect()

    assert snap.data["variable:max_connections"] == "151"
