"""Collector that captures running Docker container state."""
from __future__ import annotations

import re
from typing import Any

try:
    import docker  # type: ignore
except ImportError:  # pragma: no cover
    docker = None  # type: ignore

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class DockerCollector(BaseCollector):
    """Collect metadata about running (or all) Docker containers."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._all: bool = config.get("all", False)
        self._name_pattern: str | None = config.get("name_pattern")
        self._label_filter: dict[str, str] = config.get("label_filter", {})

    def validate_config(self) -> None:
        if docker is None:
            raise ImportError(
                "docker package is required for DockerCollector: pip install docker"
            )
        if self._name_pattern is not None:
            try:
                re.compile(self._name_pattern)
            except re.error as exc:
                raise ValueError(f"Invalid name_pattern regex: {exc}") from exc
        if not isinstance(self._label_filter, dict):
            raise ValueError("label_filter must be a dict of str -> str")

    def collect(self) -> ConfigSnapshot:
        client = docker.from_env()
        filters: dict[str, Any] = {}
        if self._label_filter:
            filters["label"] = [
                f"{k}={v}" for k, v in self._label_filter.items()
            ]
        containers = client.containers.list(all=self._all, filters=filters)

        data: dict[str, Any] = {}
        for c in containers:
            name = c.name
            if self._name_pattern and not re.search(self._name_pattern, name):
                continue
            data[name] = {
                "id": c.short_id,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "labels": c.labels,
            }
        client.close()
        return ConfigSnapshot(source="docker", data=data)
