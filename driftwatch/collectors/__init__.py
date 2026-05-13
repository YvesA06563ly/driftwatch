"""Collector registry — maps type names to collector classes."""
from __future__ import annotations

from typing import Dict, List, Type

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
from driftwatch.collectors.mysql_collector import MySQLCollector
from driftwatch.collectors.ssl_collector import SslCollector
from driftwatch.collectors.prometheus_collector import PrometheusCollector
from driftwatch.collectors.nomad_collector import NomadCollector
from driftwatch.collectors.terraform_collector import TerraformCollector
from driftwatch.collectors.syslog_collector import SyslogCollector
from driftwatch.collectors.grafana_collector import GrafanaCollector
from driftwatch.collectors.cloudwatch_collector import CloudWatchCollector
from driftwatch.collectors.azure_collector import AzureCollector

_REGISTRY: Dict[str, Type[BaseCollector]] = {
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
    "mysql": MySQLCollector,
    "ssl": SslCollector,
    "prometheus": PrometheusCollector,
    "nomad": NomadCollector,
    "terraform": TerraformCollector,
    "syslog": SyslogCollector,
    "grafana": GrafanaCollector,
    "cloudwatch": CloudWatchCollector,
    "azure": AzureCollector,
}


def list_collectors() -> List[str]:
    """Return sorted list of registered collector type names."""
    return sorted(_REGISTRY.keys())


def get_collector(config: dict) -> BaseCollector:
    """Instantiate and return a validated collector from *config*.

    The dict must contain a ``type`` key whose value matches a registered
    collector name.  All remaining keys are forwarded to the collector.

    Raises
    ------
    KeyError
        If ``type`` is missing or unknown.
    ValueError
        If the collector's ``validate_config`` rejects the configuration.
    """
    collector_type = config.get("type", "")
    if collector_type not in _REGISTRY:
        raise KeyError(f"Unknown collector type: {collector_type!r}")
    cls = _REGISTRY[collector_type]
    instance = cls({k: v for k, v in config.items() if k != "type"})
    return instance
