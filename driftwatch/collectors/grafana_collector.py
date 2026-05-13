"""Collector that snapshots Grafana dashboard and datasource configurations."""
from __future__ import annotations

import re
from typing import Any

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class GrafanaCollector(BaseCollector):
    """Collect Grafana dashboard UIDs/versions and datasource names/types."""

    name = "grafana"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "").rstrip("/")
        self._api_key: str = config.get("api_key", "")
        self._resources: list[str] = config.get("resources", ["dashboards", "datasources"])
        self._pattern: str | None = config.get("pattern")
        self._timeout: int = int(config.get("timeout", 10))

    def validate_config(self) -> None:
        if not self._url:
            raise ValueError("grafana collector requires a non-empty 'url'")
        if not self._url.startswith(("http://", "https://")):
            raise ValueError("grafana 'url' must start with http:// or https://")
        if not self._api_key:
            raise ValueError("grafana collector requires a non-empty 'api_key'")
        valid = {"dashboards", "datasources"}
        unknown = set(self._resources) - valid
        if unknown:
            raise ValueError(f"unknown grafana resources: {sorted(unknown)}")
        if not self._resources:
            raise ValueError("grafana collector requires at least one resource")
        if self._pattern:
            re.compile(self._pattern)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _matches(self, name: str) -> bool:
        if self._pattern is None:
            return True
        return bool(re.search(self._pattern, name))

    def collect(self) -> ConfigSnapshot:
        data: dict[str, Any] = {}
        session = requests.Session()
        session.headers.update(self._headers())

        if "dashboards" in self._resources:
            resp = session.get(f"{self._url}/api/search?type=dash-db", timeout=self._timeout)
            resp.raise_for_status()
            for dash in resp.json():
                title = dash.get("title", "")
                if self._matches(title):
                    uid = dash.get("uid", "")
                    data[f"dashboard:{uid}"] = {
                        "title": title,
                        "uid": uid,
                        "version": dash.get("version"),
                        "folderTitle": dash.get("folderTitle", ""),
                    }

        if "datasources" in self._resources:
            resp = session.get(f"{self._url}/api/datasources", timeout=self._timeout)
            resp.raise_for_status()
            for ds in resp.json():
                ds_name = ds.get("name", "")
                if self._matches(ds_name):
                    data[f"datasource:{ds_name}"] = {
                        "type": ds.get("type"),
                        "url": ds.get("url"),
                        "access": ds.get("access"),
                        "isDefault": ds.get("isDefault", False),
                    }

        return ConfigSnapshot(source=self.name, data=data)
