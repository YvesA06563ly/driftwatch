"""MySQL configuration collector — captures runtime variables and status."""
from __future__ import annotations

import re
from typing import Any

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class MySQLCollector(BaseCollector):
    """Collect MySQL global variables and/or status variables via a DSN."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._dsn: str = config.get("dsn", "")
        self._variables: list[str] = config.get("variables", [])
        self._status: list[str] = config.get("status", [])
        self._pattern: str | None = config.get("pattern")

    # ------------------------------------------------------------------
    def validate_config(self) -> None:
        if not self._dsn:
            raise ValueError("MySQLCollector requires a non-empty 'dsn'")
        if not self._variables and not self._status and not self._pattern:
            raise ValueError(
                "MySQLCollector requires at least one of 'variables', 'status', or 'pattern'"
            )
        if self._pattern:
            try:
                re.compile(self._pattern)
            except re.error as exc:
                raise ValueError(f"Invalid 'pattern': {exc}") from exc

    # ------------------------------------------------------------------
    def collect(self) -> ConfigSnapshot:
        try:
            import pymysql  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pymysql is required for MySQLCollector") from exc

        conn = pymysql.connect(read_default_file=None, **self._parse_dsn(self._dsn))
        data: dict[str, str] = {}
        try:
            with conn.cursor() as cur:
                if self._variables or self._pattern:
                    cur.execute("SHOW GLOBAL VARIABLES")
                    for name, value in cur.fetchall():
                        if self._matches(name):
                            data[f"variable:{name}"] = str(value)
                if self._status or self._pattern:
                    cur.execute("SHOW GLOBAL STATUS")
                    for name, value in cur.fetchall():
                        if self._matches_status(name):
                            data[f"status:{name}"] = str(value)
        finally:
            conn.close()

        return ConfigSnapshot(source=self._dsn, data=data)

    # ------------------------------------------------------------------
    def _matches(self, name: str) -> bool:
        if self._variables and name in self._variables:
            return True
        if self._pattern and re.search(self._pattern, name):
            return True
        return False

    def _matches_status(self, name: str) -> bool:
        if self._status and name in self._status:
            return True
        if self._pattern and re.search(self._pattern, name):
            return True
        return False

    @staticmethod
    def _parse_dsn(dsn: str) -> dict[str, Any]:
        """Parse a simple mysql://user:pass@host:port/db DSN."""
        import urllib.parse as up

        parsed = up.urlparse(dsn)
        kwargs: dict[str, Any] = {
            "host": parsed.hostname or "127.0.0.1",
            "port": parsed.port or 3306,
            "db": (parsed.path or "/").lstrip("/") or None,
        }
        if parsed.username:
            kwargs["user"] = parsed.username
        if parsed.password:
            kwargs["password"] = parsed.password
        return kwargs
