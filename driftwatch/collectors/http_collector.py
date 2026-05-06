"""HTTP endpoint collector — captures status code, headers, and response time."""
from __future__ import annotations

import time
from typing import Any

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class HttpCollector(BaseCollector):
    """Collect observable state from one or more HTTP endpoints."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self.urls: list[str] = config.get("urls", [])
        self.timeout: float = float(config.get("timeout", 5.0))
        self.capture_headers: list[str] = [
            h.lower() for h in config.get("capture_headers", [])
        ]
        self.method: str = config.get("method", "GET").upper()

    def validate_config(self) -> None:
        if not self.urls:
            raise ValueError(f"[{self.name}] 'urls' must be a non-empty list")
        for url in self.urls:
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise ValueError(f"[{self.name}] invalid url: {url!r}")
        if self.timeout <= 0:
            raise ValueError(f"[{self.name}] 'timeout' must be positive")

    def collect(self) -> ConfigSnapshot:
        data: dict[str, Any] = {}
        for url in self.urls:
            entry: dict[str, Any] = {}
            try:
                start = time.monotonic()
                resp = requests.request(
                    self.method, url, timeout=self.timeout, allow_redirects=True
                )
                elapsed = time.monotonic() - start
                entry["status_code"] = resp.status_code
                entry["elapsed_ms"] = round(elapsed * 1000, 2)
                entry["reachable"] = True
                for header in self.capture_headers:
                    entry[f"header:{header}"] = resp.headers.get(header)
            except requests.RequestException as exc:
                entry["reachable"] = False
                entry["error"] = type(exc).__name__
            data[url] = entry
        return ConfigSnapshot(collector=self.name, data=data)
