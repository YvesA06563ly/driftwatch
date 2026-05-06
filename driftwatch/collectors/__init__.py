"""Collector registry — maps collector type names to their classes."""
from __future__ import annotations

from typing import Any, Dict, List

from driftwatch.collectors.base import BaseCollector
from driftwatch.collectors.env_collector import EnvCollector
from driftwatch.collectors.file_collector import FileCollector
from driftwatch.collectors.process_collector import ProcessCollector
from driftwatch.collectors.http_collector import HttpCollector
from driftwatch.collectors.docker_collector import DockerCollector
from driftwatch.collectors.systemd_collector import SystemdCollector

_REGISTRY: Dict[str, type] = {
    "env": EnvCollector,
    "file": FileCollector,
    "process": ProcessCollector,
    "http": HttpCollector,
    "docker": DockerCollector,
    "systemd": SystemdCollector,
}


def list_collectors() -> List[str]:
    """Return the names of all registered collector types."""
    return list(_REGISTRY.keys())


def get_collector(collector_type: str, config: Dict[str, Any]) -> BaseCollector:
    """Instantiate and validate a collector by type name.

    Raises
    ------
    KeyError
        If *collector_type* is not registered.
    ValueError
        If the supplied *config* is invalid for the requested collector.
    """
    cls = _REGISTRY[collector_type]
    instance: BaseCollector = cls(config)
    instance.validate_config()
    return instance
