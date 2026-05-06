"""Collector that snapshots systemd unit states via systemctl."""
from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, List, Optional

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class SystemdCollector(BaseCollector):
    """Collect the active/enabled state of systemd units."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._units: List[str] = config.get("units", [])
        self._pattern: Optional[str] = config.get("pattern")
        self._include_inactive: bool = bool(config.get("include_inactive", False))

    def validate_config(self) -> None:
        if not self._units and not self._pattern:
            raise ValueError(
                "systemd collector requires at least 'units' list or 'pattern'"
            )
        if self._pattern:
            try:
                re.compile(self._pattern)
            except re.error as exc:
                raise ValueError(f"Invalid pattern '{self._pattern}': {exc}") from exc

    def _list_units(self) -> List[str]:
        """Return unit names from systemctl list-units."""
        result = subprocess.run(
            ["systemctl", "list-units", "--all", "--no-pager", "--plain",
             "--no-legend", "--output=json"],
            capture_output=True, text=True, check=False
        )
        names: List[str] = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts:
                names.append(parts[0])
        return names

    def _query_unit(self, unit: str) -> Dict[str, str]:
        result = subprocess.run(
            ["systemctl", "show", unit,
             "--property=ActiveState,SubState,LoadState,UnitFileState"],
            capture_output=True, text=True, check=False
        )
        props: Dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                props[k] = v
        return props

    def collect(self) -> ConfigSnapshot:
        units = list(self._units)
        if self._pattern:
            rx = re.compile(self._pattern)
            units += [u for u in self._list_units() if rx.search(u)]
        units = sorted(set(units))

        data: Dict[str, Any] = {}
        for unit in units:
            props = self._query_unit(unit)
            if not self._include_inactive and props.get("ActiveState") == "inactive":
                continue
            data[unit] = props

        return ConfigSnapshot(source="systemd", data=data)
