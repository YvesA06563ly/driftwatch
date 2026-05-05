"""Collector that snapshots file metadata (mtime, size, checksum) for drift detection."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class FileCollector(BaseCollector):
    """Collects metadata and optional checksums for a list of watched files."""

    REQUIRED_KEYS = ("paths",)

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._paths: list[str] = config["paths"]
        self._checksum: bool = config.get("checksum", True)
        self._algorithm: str = config.get("algorithm", "sha256")

    def validate_config(self) -> None:
        for key in self.REQUIRED_KEYS:
            if key not in self.config:
                raise ValueError(f"FileCollector requires config key: '{key}'")
        if not isinstance(self.config["paths"], list):
            raise TypeError("'paths' must be a list of file path strings")
        if self._algorithm not in hashlib.algorithms_guaranteed:
            raise ValueError(f"Unsupported checksum algorithm: '{self._algorithm}'")

    def _file_metadata(self, path: str) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"exists": False}
        stat = p.stat()
        meta: dict[str, Any] = {
            "exists": True,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }
        if self._checksum:
            meta["checksum"] = self._compute_checksum(p)
        return meta

    def _compute_checksum(self, path: Path) -> str:
        h = hashlib.new(self._algorithm)
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def collect(self) -> ConfigSnapshot:
        data = {path: self._file_metadata(path) for path in self._paths}
        return ConfigSnapshot(source="file", data=data)
