"""Collector that reads key/value pairs from a Consul KV store."""
from __future__ import annotations

import re
from typing import Any

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class ConsulCollector(BaseCollector):
    """Collect key/value entries from Consul's HTTP API.

    Config keys
    -----------
    url : str
        Base URL of the Consul agent, e.g. ``http://localhost:8500``.
    prefix : str, optional
        KV path prefix to recurse under (default ``""``).
    pattern : str, optional
        Regex applied to each key; only matching keys are included.
    token : str, optional
        Consul ACL token sent as the ``X-Consul-Token`` header.
    timeout : float, optional
        HTTP request timeout in seconds (default ``5.0``).
    """

    NAME = "consul"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "http://localhost:8500").rstrip("/")
        self._prefix: str = config.get("prefix", "")
        self._pattern: re.Pattern | None = (
            re.compile(config["pattern"]) if "pattern" in config else None
        )
        self._token: str | None = config.get("token")
        self._timeout: float = float(config.get("timeout", 5.0))

    def validate_config(self) -> None:
        url = self._config.get("url", "")
        if url and not url.startswith(("http://", "https://")):
            raise ValueError("consul collector 'url' must start with http:// or https://")
        if "pattern" in self._config:
            try:
                re.compile(self._config["pattern"])
            except re.error as exc:
                raise ValueError(f"consul collector invalid 'pattern': {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        headers: dict[str, str] = {}
        if self._token:
            headers["X-Consul-Token"] = self._token

        endpoint = f"{self._url}/v1/kv/{self._prefix.lstrip('/')}?recurse"
        try:
            resp = requests.get(endpoint, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
            entries: list[dict] = resp.json() or []
        except requests.RequestException as exc:
            return ConfigSnapshot(data={"error": str(exc)})

        import base64

        data: dict[str, str] = {}
        for entry in entries:
            key: str = entry.get("Key", "")
            raw = entry.get("Value")
            value = base64.b64decode(raw).decode("utf-8", errors="replace") if raw else ""
            if self._pattern and not self._pattern.search(key):
                continue
            data[key] = value

        return ConfigSnapshot(data=data)
