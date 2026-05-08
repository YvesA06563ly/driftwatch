"""SSL/TLS certificate collector — captures expiry, issuer, and subject for hostnames."""
from __future__ import annotations

import re
import socket
import ssl
from datetime import datetime, timezone
from typing import Any

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot

_DATE_FMT = "%b %d %H:%M:%S %Y %Z"


class SslCollector(BaseCollector):
    """Collect TLS certificate metadata for a list of hostnames."""

    collector_type = "ssl"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._hostnames: list[str] = config.get("hostnames", [])
        self._port: int = int(config.get("port", 443))
        self._timeout: float = float(config.get("timeout", 5.0))

    def validate_config(self) -> None:
        hostnames = self._config.get("hostnames")
        if not hostnames or not isinstance(hostnames, list):
            raise ValueError("ssl collector requires a non-empty 'hostnames' list")
        for h in hostnames:
            if not isinstance(h, str) or not h.strip():
                raise ValueError(f"invalid hostname entry: {h!r}")
        port = self._config.get("port", 443)
        if not (1 <= int(port) <= 65535):
            raise ValueError(f"'port' must be between 1 and 65535, got {port}")

    def collect(self) -> ConfigSnapshot:
        data: dict[str, Any] = {}
        ctx = ssl.create_default_context()
        for hostname in self._hostnames:
            key = f"{hostname}:{self._port}"
            try:
                with socket.create_connection(
                    (hostname, self._port), timeout=self._timeout
                ) as sock:
                    with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                not_after = datetime.strptime(
                    cert["notAfter"], _DATE_FMT
                ).replace(tzinfo=timezone.utc)
                not_before = datetime.strptime(
                    cert["notBefore"], _DATE_FMT
                ).replace(tzinfo=timezone.utc)
                now = datetime.now(tz=timezone.utc)
                days_remaining = (not_after - now).days
                subject = dict(x[0] for x in cert.get("subject", []))
                issuer = dict(x[0] for x in cert.get("issuer", []))
                data[key] = {
                    "status": "ok",
                    "subject_cn": subject.get("commonName", ""),
                    "issuer_cn": issuer.get("commonName", ""),
                    "not_before": not_before.isoformat(),
                    "not_after": not_after.isoformat(),
                    "days_remaining": days_remaining,
                    "expired": days_remaining < 0,
                    "serial": cert.get("serialNumber", ""),
                }
            except Exception as exc:  # noqa: BLE001
                data[key] = {"status": "error", "error": str(exc)}
        return ConfigSnapshot(source=self.collector_type, data=data)
