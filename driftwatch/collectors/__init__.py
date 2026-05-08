"""Collector registry – maps collector type names to their classes."""
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
from driftwatch.collectors.vault_collector import VaultCollector
from driftwatch.collectors.redis_collector import RedisCollector
from driftwatch.collectors.etcd_collector import EtcdCollector
from driftwatch.collectors.postgres_collector import PostgresCollector
from driftwatch.collectors.snmp_collector import SnmpCollector
from driftwatch.collectors.dns_collector import DnsCollector

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
    "vault": VaultCollector,
    "redis": RedisCollector,
    "etcd": EtcdCollector,
    "postgres": PostgresCollector,
    "snmp": SnmpCollector,
    "dns": DnsCollector,
}


def list_collectors() -> List[str]:
    """Return sorted list of registered collector type names."""
    return sorted(_REGISTRY.keys())


def get_collector(collector_type: str, config: Dict[str, Any]) -> BaseCollector:
    """Instantiate and validate a collector by type name.

    Raises
    ------
    ValueError
        If *collector_type* is unknown or the config fails validation.
    """
    if collector_type not in _REGISTRY:
        raise ValueError(
            f"unknown collector type {collector_type!r}; "
            f"available: {list_collectors()}"
        )
    instance = _REGISTRY[collector_type](config)
    instance.validate_config()
    return instance
