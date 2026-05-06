"""Collector registry — maps type strings to collector classes."""
from __future__ import annotations

from typing import Any

from driftwatch.collectors.env_collector import EnvCollector
from driftwatch.collectors.file_collector import FileCollector
from driftwatch.collectors.http_collector import HttpCollector
from driftwatch.collectors.process_collector import ProcessCollector

_REGISTRY: dict[str, type] = {
    "env": EnvCollector,
    "file": FileCollector,
    "process": ProcessCollector,
    "http": HttpCollector,
}


def get_collector(collector_type: str, name: str, config: dict[str, Any]):
    """Instantiate and return a validated collector by type string.

    Raises
    ------
    ValueError
        If *collector_type* is not registered.
    """
    cls = _REGISTRY.get(collector_type)
    if cls is None:
        raise ValueError(
            f"Unknown collector type {collector_type!r}. "
            f"Available: {list(_REGISTRY)}"
        )
    instance = cls(name, config)
    instance.validate_config()
    return instance


def list_collectors() -> list[str]:
    """Return sorted list of registered collector type strings."""
    return sorted(_REGISTRY.keys())
