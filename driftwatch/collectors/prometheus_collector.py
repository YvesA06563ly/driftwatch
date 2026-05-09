"""Collector that scrapes Prometheus metrics endpoints and captures gauge/counter values."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class PrometheusCollector(BaseCollector):
    """Scrape one or more Prometheus /metrics endpoints and snapshot selected metrics."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._urls: List[str] = config.get("urls", [])
        self._metric_pattern: Optional[str] = config.get("metric_pattern")
        self._compiled: Optional[re.Pattern] = (
            re.compile(self._metric_pattern) if self._metric_pattern else None
        )
        self._timeout: int = int(config.get("timeout", 10))

    def validate_config(self) -> None:
        if not self._urls:
            raise ValueError("prometheus collector requires at least one url")
        for url in self._urls:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"invalid prometheus url: {url!r}")
        if self._metric_pattern:
            try:
                re.compile(self._metric_pattern)
            except re.error as exc:
                raise ValueError(f"invalid metric_pattern: {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        data: Dict[str, Any] = {}
        for url in self._urls:
            try:
                resp = requests.get(url, timeout=self._timeout)
                resp.raise_for_status()
                data[url] = self._parse_exposition(resp.text)
            except Exception as exc:  # noqa: BLE001
                data[url] = {"error": str(exc)}
        return ConfigSnapshot(collector=self.name, data=data)

    def _parse_exposition(self, text: str) -> Dict[str, str]:
        """Parse Prometheus text exposition format, returning metric_name -> value."""
        result: Dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue
            metric_name, value = parts[0].strip(), parts[1].strip()
            if self._compiled and not self._compiled.search(metric_name):
                continue
            result[metric_name] = value
        return result
