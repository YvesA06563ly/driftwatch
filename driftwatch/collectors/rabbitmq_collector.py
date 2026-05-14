"""Collector that snapshots RabbitMQ queue and exchange state via the Management API."""

from __future__ import annotations

import re
from typing import Any

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class RabbitMQCollector(BaseCollector):
    """Collect queue/exchange metadata from a RabbitMQ Management HTTP API endpoint."""

    name = "rabbitmq"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "http://localhost:15672").rstrip("/")
        self._username: str = config.get("username", "guest")
        self._password: str = config.get("password", "guest")
        self._vhost: str = config.get("vhost", "%2F")
        self._resources: list[str] = config.get("resources", ["queues", "exchanges"])
        self._name_pattern: str | None = config.get("name_pattern")
        self._timeout: int = int(config.get("timeout", 10))
        self._compiled: re.Pattern[str] | None = (
            re.compile(self._name_pattern) if self._name_pattern else None
        )

    def validate_config(self) -> None:
        if not self._url:
            raise ValueError("rabbitmq collector requires a non-empty 'url'")
        valid_resources = {"queues", "exchanges"}
        for r in self._resources:
            if r not in valid_resources:
                raise ValueError(
                    f"rabbitmq collector: unknown resource '{r}'; "
                    f"valid options are {sorted(valid_resources)}"
                )
        if self._name_pattern:
            try:
                re.compile(self._name_pattern)
            except re.error as exc:
                raise ValueError(
                    f"rabbitmq collector: invalid name_pattern: {exc}"
                ) from exc

    def collect(self) -> ConfigSnapshot:
        data: dict[str, Any] = {}
        auth = (self._username, self._password)
        for resource in self._resources:
            endpoint = f"{self._url}/api/{resource}/{self._vhost}"
            resp = requests.get(endpoint, auth=auth, timeout=self._timeout)
            resp.raise_for_status()
            items: list[dict[str, Any]] = resp.json()
            for item in items:
                item_name: str = item.get("name", "")
                if self._compiled and not self._compiled.search(item_name):
                    continue
                key = f"{resource}/{item_name}"
                if resource == "queues":
                    data[key] = {
                        "messages": item.get("messages", 0),
                        "consumers": item.get("consumers", 0),
                        "state": item.get("state", "unknown"),
                        "durable": item.get("durable", False),
                    }
                else:
                    data[key] = {
                        "type": item.get("type", "unknown"),
                        "durable": item.get("durable", False),
                        "auto_delete": item.get("auto_delete", False),
                    }
        return ConfigSnapshot(source=self.name, data=data)
