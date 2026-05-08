"""Collector that reads key/value pairs from an etcd v3 cluster via its HTTP API."""

from __future__ import annotations

import base64
import re
from typing import Any

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class EtcdCollector(BaseCollector):
    """Collect keys from an etcd v3 cluster using the gRPC-gateway REST API.

    Config keys:
        url       (str)  – base URL, e.g. "http://localhost:2379"  (required)
        key_prefix (str) – only return keys that start with this prefix
        pattern   (str)  – optional regex applied to key names after prefix filter
        timeout   (int)  – HTTP timeout in seconds (default: 5)
    """

    NAME = "etcd"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "").rstrip("/")
        self._key_prefix: str = config.get("key_prefix", "")
        self._pattern: re.Pattern[str] | None = (
            re.compile(config["pattern"]) if "pattern" in config else None
        )
        self._timeout: int = int(config.get("timeout", 5))

    def validate_config(self) -> None:
        if not self._url:
            raise ValueError("EtcdCollector requires a non-empty 'url'")
        if "pattern" in self._config:
            try:
                re.compile(self._config["pattern"])
            except re.error as exc:
                raise ValueError(f"EtcdCollector 'pattern' is invalid: {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        endpoint = f"{self._url}/v3/kv/range"

        # etcd range request: encode key prefix as base64
        key_b64 = base64.b64encode(
            (self._key_prefix or "\x00").encode()
        ).decode()
        # range_end '\x00' means "all keys >= key" when key is '\x00',
        # or all keys with the given prefix when constructed properly.
        range_end_b64 = base64.b64encode(b"\x00").decode()
        payload: dict[str, Any] = {"key": key_b64, "range_end": range_end_b64}

        resp = requests.post(endpoint, json=payload, timeout=self._timeout)
        resp.raise_for_status()

        data: dict[str, Any] = {}
        for kv in resp.json().get("kvs") or []:
            raw_key = base64.b64decode(kv["key"]).decode(errors="replace")
            raw_val = base64.b64decode(kv.get("value", "")).decode(errors="replace")
            if self._pattern and not self._pattern.search(raw_key):
                continue
            data[raw_key] = raw_val

        return ConfigSnapshot(source=self.NAME, data=data)
