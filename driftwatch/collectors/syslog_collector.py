"""Collector that samples recent syslog / journald entries as configuration state.

The snapshot captures the *count* and *latest timestamp* for each matched
unit/program so that unexpected silences or bursts are detected as drift.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from typing import Any

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class SyslogCollector(BaseCollector):
    """Collect log activity statistics from journald via ``journalctl``."""

    name = "syslog"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._units: list[str] = config.get("units", [])
        self._pattern: str | None = config.get("pattern")
        self._since: str = config.get("since", "1h")
        self._compiled: re.Pattern | None = (
            re.compile(self._pattern) if self._pattern else None
        )

    # ------------------------------------------------------------------
    def validate_config(self) -> None:
        if not self._units and not self._pattern:
            raise ValueError(
                "syslog collector requires at least 'units' or 'pattern'"
            )
        if self._pattern:
            try:
                re.compile(self._pattern)
            except re.error as exc:
                raise ValueError(f"Invalid 'pattern' regex: {exc}") from exc

    # ------------------------------------------------------------------
    def _query_unit(self, unit: str) -> dict[str, Any]:
        """Run journalctl for *unit* and return count + latest timestamp."""
        cmd = [
            "journalctl",
            "--unit", unit,
            "--since", f"-{self._since}",
            "--output", "short-iso",
            "--no-pager",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            lines = [l for l in result.stdout.splitlines() if l.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            lines = []

        return {
            "count": len(lines),
            "latest": lines[-1][:25] if lines else None,
        }

    # ------------------------------------------------------------------
    def _list_units(self) -> list[str]:
        """Return all active units whose name matches self._compiled."""
        cmd = ["systemctl", "list-units", "--no-pager", "--plain", "--all"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        units: list[str] = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts and self._compiled and self._compiled.search(parts[0]):
                units.append(parts[0])
        return units

    # ------------------------------------------------------------------
    def collect(self) -> ConfigSnapshot:
        units = list(self._units)
        if self._compiled:
            units.extend(u for u in self._list_units() if u not in units)

        data: dict[str, Any] = {}
        for unit in units:
            data[unit] = self._query_unit(unit)

        return ConfigSnapshot(
            collector=self.name,
            data=data,
            collected_at=datetime.now(timezone.utc).isoformat(),
        )
