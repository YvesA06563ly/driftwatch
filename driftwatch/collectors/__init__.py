"""Collector registry — maps type names to collector classes."""
from __future__ import annotations

from typing import Any

from driftwatch.collectors.base import BaseCollector
from driftwatch.collectors.env_collector import EnvCollector
from driftwatch.collectors.file_collector import FileCollector
from driftwatch.collectors.process_collector import ProcessCollector
from driftwatch.collectors.http_collector import HttpCollector
from driftwatch.collectors.docker_collector import DockerCollector

_REGISTRY: dict[str, type[BaseCollector]] = {
    "env": EnvCollector,
    "file": FileCollector,
    "process": ProcessCollector,
    "http": HttpCollector,
    "docker": DockerCollector,
}


def get_collector(collector_type: str, config: dict[str, Any]) -> BaseCollector:
    """Instantiate and return a collector by type name.

    Raises
    ------
    ValueError
        If *collector_type* is not registered.
    """
    try:
        cls = _REGISTRY[collector_type]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown collector type '{collector_type}'. Known types: {known}"
        )
    return cls(config)


def list_collectors() -> list[str]:
    """Return sorted list of registered collector type names."""
    return sorted(_REGISTRY.keys())
