"""Collector registry — maps collector type names to their classes."""
from __future__ import annotations

from typing import Any

from driftwatch.collectors.aws_collector import AwsCollector
from driftwatch.collectors.base import BaseCollector
from driftwatch.collectors.consul_collector import ConsulCollector
from driftwatch.collectors.docker_collector import DockerCollector
from driftwatch.collectors.env_collector import EnvCollector
from driftwatch.collectors.file_collector import FileCollector
from driftwatch.collectors.git_collector import GitCollector
from driftwatch.collectors.http_collector import HttpCollector
from driftwatch.collectors.process_collector import ProcessCollector
from driftwatch.collectors.systemd_collector import SystemdCollector

_REGISTRY: dict[str, type[BaseCollector]] = {
    "aws": AwsCollector,
    "consul": ConsulCollector,
    "docker": DockerCollector,
    "env": EnvCollector,
    "file": FileCollector,
    "git": GitCollector,
    "http": HttpCollector,
    "process": ProcessCollector,
    "systemd": SystemdCollector,
}


def list_collectors() -> list[str]:
    """Return the names of all registered collector types."""
    return sorted(_REGISTRY.keys())


def get_collector(collector_type: str, config: dict[str, Any]) -> BaseCollector:
    """Instantiate and validate a collector by type name.

    Parameters
    ----------
    collector_type:
        One of the keys returned by :func:`list_collectors`.
    config:
        Collector-specific configuration dict.

    Raises
    ------
    KeyError
        If *collector_type* is not registered.
    ValueError
        If the provided *config* fails the collector's own validation.
    """
    if collector_type not in _REGISTRY:
        raise KeyError(
            f"Unknown collector type '{collector_type}'. "
            f"Available: {list_collectors()}"
        )
    instance = _REGISTRY[collector_type](config)
    instance.validate_config()
    return instance
