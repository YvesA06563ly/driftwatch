"""SNMP OID collector — polls SNMP OIDs via pysnmp and snapshots their values."""
from __future__ import annotations

import re
from typing import Any

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class SnmpCollector(BaseCollector):
    """Collect SNMP OID values from one or more targets.

    Config keys:
        targets   (list[str], required) – host[:port] strings, default port 161.
        oids      (list[str], required) – OIDs or symbolic names to poll.
        community (str, optional)       – SNMP v2c community, default 'public'.
        timeout   (int, optional)       – per-request timeout seconds, default 5.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._targets: list[str] = config.get("targets", [])
        self._oids: list[str] = config.get("oids", [])
        self._community: str = config.get("community", "public")
        self._timeout: int = int(config.get("timeout", 5))

    # ------------------------------------------------------------------
    def validate_config(self) -> None:
        if not self._targets:
            raise ValueError("snmp_collector: 'targets' must be a non-empty list")
        for t in self._targets:
            if not isinstance(t, str) or not t.strip():
                raise ValueError(f"snmp_collector: invalid target {t!r}")
        if not self._oids:
            raise ValueError("snmp_collector: 'oids' must be a non-empty list")
        if self._timeout < 1:
            raise ValueError("snmp_collector: 'timeout' must be >= 1")

    # ------------------------------------------------------------------
    def collect(self) -> ConfigSnapshot:
        """Poll each target for every OID and return a flat snapshot.

        Keys are formatted as  '<host>:<port>/<oid>'.
        Values are the string representation returned by pysnmp, or
        '__error__:<message>' when a target is unreachable.
        """
        try:
            from pysnmp.hlapi import (
                CommunityData,
                ContextData,
                ObjectIdentity,
                ObjectType,
                SnmpEngine,
                UdpTransportTarget,
                getCmd,
            )
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pysnmp is required for SnmpCollector: pip install pysnmp"
            ) from exc

        data: dict[str, Any] = {}

        for raw_target in self._targets:
            host, _, port_str = raw_target.partition(":")
            port = int(port_str) if port_str else 161
            endpoint = f"{host}:{port}"

            for oid in self._oids:
                key = f"{endpoint}/{oid}"
                try:
                    error_indication, error_status, _, var_binds = next(
                        getCmd(
                            SnmpEngine(),
                            CommunityData(self._community, mpModel=1),
                            UdpTransportTarget(
                                (host, port), timeout=self._timeout, retries=1
                            ),
                            ContextData(),
                            ObjectType(ObjectIdentity(oid)),
                        )
                    )
                    if error_indication:
                        data[key] = f"__error__:{error_indication}"
                    elif error_status:
                        data[key] = f"__error__:{error_status.prettyPrint()}"
                    else:
                        _name, val = var_binds[0]
                        data[key] = val.prettyPrint()
                except Exception as exc:  # noqa: BLE001
                    data[key] = f"__error__:{exc}"

        return ConfigSnapshot(source="snmp", data=data)
