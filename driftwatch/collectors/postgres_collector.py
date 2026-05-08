"""Collector that snapshots PostgreSQL configuration parameters and replication state."""
from __future__ import annotations

import re
from typing import Any

try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot

_DEFAULT_PARAMS = [
    "max_connections",
    "shared_buffers",
    "work_mem",
    "maintenance_work_mem",
    "wal_level",
    "max_wal_senders",
    "synchronous_commit",
    "log_min_duration_statement",
]


class PostgresCollector(BaseCollector):
    """Collect pg_settings rows and optional replication slot state."""

    name = "postgres"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._dsn: str = config.get("dsn", "")
        self._params: list[str] = config.get("parameters", _DEFAULT_PARAMS)
        self._param_pattern: str | None = config.get("param_pattern")
        self._include_replication: bool = bool(config.get("include_replication", False))

    def validate_config(self) -> None:
        if not self._dsn:
            raise ValueError("postgres collector requires a non-empty 'dsn'")
        if self._param_pattern:
            try:
                re.compile(self._param_pattern)
            except re.error as exc:
                raise ValueError(f"invalid param_pattern: {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed; run: pip install psycopg2-binary")

        data: dict[str, Any] = {}
        conn = psycopg2.connect(self._dsn)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if self._param_pattern:
                    cur.execute(
                        "SELECT name, setting FROM pg_settings WHERE name ~ %s ORDER BY name",
                        (self._param_pattern,),
                    )
                else:
                    placeholders = ",".join("%s" for _ in self._params)
                    cur.execute(
                        f"SELECT name, setting FROM pg_settings WHERE name IN ({placeholders}) ORDER BY name",
                        self._params,
                    )
                for row in cur.fetchall():
                    data[f"setting:{row['name']}"] = row["setting"]

                if self._include_replication:
                    cur.execute(
                        "SELECT slot_name, slot_type, active, restart_lsn::text FROM pg_replication_slots ORDER BY slot_name"
                    )
                    for row in cur.fetchall():
                        prefix = f"replication_slot:{row['slot_name']}"
                        data[f"{prefix}:type"] = row["slot_type"]
                        data[f"{prefix}:active"] = str(row["active"])
                        data[f"{prefix}:restart_lsn"] = row["restart_lsn"] or ""
        finally:
            conn.close()

        return ConfigSnapshot(source=self.name, data=data)
