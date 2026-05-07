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
from driftwatch.collectors.aws_collector import AwsCollector
from driftwatch.collectors.git_collector import GitCollector
from driftwatch.collectors.consul_collector import ConsulCollector
from driftwatch.collectors.kubernetes_collector import KubernetesCollector

_REGISTRY: Dict[str, type] = {
    "env": EnvCollector,
    "file": FileCollector,
    "process": ProcessCollector,
    "http": HttpCollector,
    "docker": DockerCollector,
    "systemd": SystemdCollector,
    "aws": AwsCollector,
    "git": GitCollector,
    "consul": ConsulCollector,
    "kubernetes": KubernetesCollector,
}


def list_collectors() -> List[str]:
    """Return the names of all registered collector types."""
    return list(_REGISTRY.keys())


def get_collector(collector_type: str, config: Dict[str, Any]) -> BaseCollector:
    """Instantiate and validate a collector by type name.

    Raises
    ------
    ValueError
        If *collector_type* is unknown or the config fails validation.
    """
    if collector_type not in _REGISTRY:
        raise ValueError(
            f"Unknown collector type '{collector_type}'. "
            f"Available: {list_collectors()}"
        )
    cls = _REGISTRY[collector_type]
    instance: BaseCollector = cls(config)
    instance.validate_config()
    return instance
