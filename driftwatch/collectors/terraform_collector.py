"""Collector that reads Terraform state files and captures resource configurations."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class TerraformCollector(BaseCollector):
    """Reads one or more Terraform state files and extracts resource attributes."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._state_files: list[str] = config.get("state_files", [])
        self._resource_pattern: str | None = config.get("resource_pattern")
        self._include_meta: bool = bool(config.get("include_meta", False))
        self._compiled: re.Pattern | None = (
            re.compile(self._resource_pattern) if self._resource_pattern else None
        )

    def validate_config(self) -> None:
        if not self._state_files:
            raise ValueError("terraform collector requires at least one 'state_files' entry")
        if self._resource_pattern:
            try:
                re.compile(self._resource_pattern)
            except re.error as exc:
                raise ValueError(f"invalid resource_pattern: {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        data: dict[str, Any] = {}
        for path_str in self._state_files:
            path = Path(path_str)
            if not path.exists():
                data[str(path)] = {"error": "state_file_not_found"}
                continue
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                data[str(path)] = {"error": str(exc)}
                continue

            resources = state.get("resources", [])
            for resource in resources:
                r_type = resource.get("type", "unknown")
                r_name = resource.get("name", "unknown")
                key = f"{r_type}.{r_name}"
                if self._compiled and not self._compiled.search(key):
                    continue
                instances = resource.get("instances", [])
                attrs = instances[0].get("attributes", {}) if instances else {}
                entry: dict[str, Any] = {"attributes": attrs}
                if self._include_meta:
                    entry["mode"] = resource.get("mode")
                    entry["provider"] = resource.get("provider")
                data[key] = entry

        return ConfigSnapshot(source=self.name, data=data)
