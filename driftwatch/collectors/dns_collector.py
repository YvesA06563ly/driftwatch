"""DNS collector – resolves hostnames and records A/AAAA/CNAME/MX answers."""
from __future__ import annotations

import re
import socket
from typing import Any, Dict, List

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class DnsCollector(BaseCollector):
    """Collect DNS resolution results for a list of hostnames."""

    name = "dns"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._hostnames: List[str] = config.get("hostnames", [])
        self._record_types: List[str] = [
            t.upper() for t in config.get("record_types", ["A"])
        ]
        self._timeout: float = float(config.get("timeout", 5.0))

    def validate_config(self) -> None:
        if not self._hostnames:
            raise ValueError("dns collector requires at least one hostname")
        allowed = {"A", "AAAA", "CNAME", "MX"}
        unknown = set(self._record_types) - allowed
        if unknown:
            raise ValueError(f"unsupported record_types: {sorted(unknown)}")
        for host in self._hostnames:
            if not re.match(r"^[A-Za-z0-9._-]+$", host):
                raise ValueError(f"invalid hostname: {host!r}")

    def collect(self) -> ConfigSnapshot:
        data: Dict[str, Any] = {}
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(self._timeout)
        try:
            for host in self._hostnames:
                host_data: Dict[str, Any] = {}
                for rtype in self._record_types:
                    host_data[rtype] = self._resolve(host, rtype)
                data[host] = host_data
        finally:
            socket.setdefaulttimeout(old_timeout)
        return ConfigSnapshot(source=self.name, data=data)

    def _resolve(self, host: str, rtype: str) -> List[str]:
        try:
            if rtype == "A":
                infos = socket.getaddrinfo(host, None, socket.AF_INET)
                return sorted({i[4][0] for i in infos})
            if rtype == "AAAA":
                infos = socket.getaddrinfo(host, None, socket.AF_INET6)
                return sorted({i[4][0] for i in infos})
            # CNAME / MX – best-effort via getaddrinfo canonical name
            return [socket.getfqdn(host)]
        except (socket.gaierror, OSError) as exc:
            return [f"ERROR: {exc}"]
