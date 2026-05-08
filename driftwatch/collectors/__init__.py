"""Collector registry – maps type names to collector classes."""
from __future__ import annotations

from typing import Any

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
from driftwatch.collectors.vault_collector import VaultCollector

_REGISTRY: dict[str, type[BaseCollector]] = {
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
    "vault": VaultCollector,
}


def list_collectors() -> list[str]:
    """Return sorted list of registered collector type names."""
    return sorted(_REGISTRY.keys())


def get_collector(collector_type: str, config: dict[str, Any]) -> BaseCollector:
    """Instantiate and validate a collector by type name.

    Raises:
        KeyError: if *collector_type* is not registered.
        ValueError: if the collector's config validation fails.
    """
    try:
        cls = _REGISTRY[collector_type]
    except KeyError:
        raise KeyError(
            f"Unknown collector type '{collector_type}'. "
            f"Available: {list_collectors()}"
        ) from None
    instance = cls(config)
    instance.validate_config()
    return instance
