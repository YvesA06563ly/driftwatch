"""Collector that reads secrets metadata from HashiCorp Vault."""
from __future__ import annotations

import re
from typing import Any

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class VaultCollector(BaseCollector):
    """Collect secret metadata (not values) from a Vault KV v2 mount."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "http://127.0.0.1:8200").rstrip("/")
        self._token: str = config.get("token", "")
        self._mount: str = config.get("mount", "secret")
        self._paths: list[str] = config.get("paths", [])
        self._pattern: str | None = config.get("pattern")
        self._timeout: int = int(config.get("timeout", 10))

    def validate_config(self) -> None:
        if not self._url:
            raise ValueError("vault_collector: 'url' must not be empty")
        if not self._token:
            raise ValueError("vault_collector: 'token' must not be empty")
        if not self._paths and not self._pattern:
            raise ValueError(
                "vault_collector: at least one of 'paths' or 'pattern' is required"
            )
        if self._pattern:
            try:
                re.compile(self._pattern)
            except re.error as exc:
                raise ValueError(
                    f"vault_collector: invalid 'pattern': {exc}"
                ) from exc

    def _headers(self) -> dict[str, str]:
        return {"X-Vault-Token": self._token}

    def _list_paths(self) -> list[str]:
        """LIST the mount root and return matching paths."""
        url = f"{self._url}/v1/{self._mount}/metadata/"
        resp = requests.request(
            "LIST", url, headers=self._headers(), timeout=self._timeout
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        keys: list[str] = resp.json().get("data", {}).get("keys", [])
        pat = re.compile(self._pattern) if self._pattern else None
        return [k for k in keys if not k.endswith("/") and (pat is None or pat.search(k))]

    def collect(self) -> ConfigSnapshot:
        paths = list(self._paths)
        if self._pattern:
            paths.extend(self._list_paths())

        data: dict[str, Any] = {}
        for path in paths:
            url = f"{self._url}/v1/{self._mount}/metadata/{path}"
            resp = requests.get(url, headers=self._headers(), timeout=self._timeout)
            if resp.status_code == 404:
                data[path] = {"exists": False}
                continue
            resp.raise_for_status()
            meta = resp.json().get("data", {})
            data[path] = {
                "exists": True,
                "version": meta.get("current_version"),
                "created_time": meta.get("created_time"),
                "updated_time": meta.get("updated_time"),
            }
        return ConfigSnapshot(source="vault", data=data)
