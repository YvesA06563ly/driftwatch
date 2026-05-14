"""Collector that reads HAProxy stats via the stats socket or HTTP endpoint."""
from __future__ import annotations

import csv
import io
import re
import socket
from typing import Any, Dict

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class HaproxyCollector(BaseCollector):
    """Collect HAProxy frontend/backend/server stats.

    Config keys:
        url (str): HTTP stats endpoint, e.g. ``http://localhost:8404/stats;csv``.
            Mutually exclusive with *socket_path*.
        socket_path (str): Path to the HAProxy stats UNIX socket.
            Mutually exclusive with *url*.
        proxy_pattern (str, optional): Regex to filter proxy names.
        timeout (int, optional): Request / socket timeout in seconds (default 5).
    """

    NAME = "haproxy"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "")
        self._socket_path: str = config.get("socket_path", "")
        self._pattern = re.compile(config["proxy_pattern"]) if config.get("proxy_pattern") else None
        self._timeout: int = int(config.get("timeout", 5))

    def validate_config(self) -> None:
        has_url = bool(self._url)
        has_sock = bool(self._socket_path)
        if not has_url and not has_sock:
            raise ValueError("haproxy collector requires 'url' or 'socket_path'")
        if has_url and has_sock:
            raise ValueError("haproxy collector: specify only one of 'url' or 'socket_path'")
        if has_url and not self._url.startswith(("http://", "https://")):
            raise ValueError("haproxy collector 'url' must start with http:// or https://")
        if self._config.get("proxy_pattern"):
            try:
                re.compile(self._config["proxy_pattern"])
            except re.error as exc:
                raise ValueError(f"haproxy collector invalid proxy_pattern: {exc}") from exc

    # ------------------------------------------------------------------
    def _fetch_csv(self) -> str:
        if self._url:
            resp = requests.get(self._url, timeout=self._timeout)
            resp.raise_for_status()
            return resp.text
        # Unix socket path
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(self._timeout)
            sock.connect(self._socket_path)
            sock.sendall(b"show stat\n")
            chunks = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks).decode()

    def collect(self) -> ConfigSnapshot:
        raw = self._fetch_csv()
        reader = csv.DictReader(io.StringIO(raw))
        data: Dict[str, Any] = {}
        for row in reader:
            proxy = row.get("# pxname") or row.get("pxname", "")
            svname = row.get("svname", "")
            if self._pattern and not self._pattern.search(proxy):
                continue
            key = f"{proxy}/{svname}"
            data[key] = {
                "status": row.get("status", ""),
                "scur": row.get("scur", "0"),
                "smax": row.get("smax", "0"),
                "ereq": row.get("ereq", "0"),
                "econ": row.get("econ", "0"),
                "eresp": row.get("eresp", "0"),
            }
        return ConfigSnapshot(source=self.NAME, data=data)
