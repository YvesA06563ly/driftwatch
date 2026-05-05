"""Collector that snapshots running process state."""

from __future__ import annotations

import re
from typing import Any

import psutil

from .base import BaseCollector, ConfigSnapshot


class ProcessCollector(BaseCollector):
    """Collect metadata about running processes matching a filter."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._name_pattern: str | None = config.get("name_pattern")
        self._pids: list[int] = config.get("pids", [])
        self._include_cmdline: bool = config.get("include_cmdline", False)

    def validate_config(self) -> None:
        if self._name_pattern is not None:
            try:
                re.compile(self._name_pattern)
            except re.error as exc:
                raise ValueError(
                    f"Invalid name_pattern regex: {self._name_pattern!r}"
                ) from exc
        if not isinstance(self._pids, list):
            raise ValueError("'pids' must be a list of integers")

    def collect(self) -> ConfigSnapshot:
        data: dict[str, Any] = {}
        pattern = (
            re.compile(self._name_pattern) if self._name_pattern else None
        )

        for proc in psutil.process_iter(["pid", "name", "status", "cmdline"]):
            try:
                info = proc.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            pid: int = info["pid"]
            name: str = info.get("name") or ""

            if self._pids and pid not in self._pids:
                continue
            if pattern and not pattern.search(name):
                continue

            entry: dict[str, Any] = {
                "name": name,
                "status": info.get("status"),
            }
            if self._include_cmdline:
                entry["cmdline"] = info.get("cmdline") or []

            data[str(pid)] = entry

        return ConfigSnapshot(source="process", data=data)
