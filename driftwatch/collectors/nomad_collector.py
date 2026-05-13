"""Collector for HashiCorp Nomad job status and allocation metadata."""
from __future__ import annotations

import re
from typing import Any

import requests

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class NomadCollector(BaseCollector):
    """Collect Nomad job statuses and allocation counts via the Nomad HTTP API."""

    name = "nomad"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "http://localhost:4646").rstrip("/")
        self._token: str | None = config.get("token")
        self._namespace: str = config.get("namespace", "default")
        self._job_pattern: re.Pattern[str] | None = (
            re.compile(config["job_pattern"]) if config.get("job_pattern") else None
        )
        self._timeout: int = int(config.get("timeout", 10))

    def validate_config(self) -> None:
        url = self._config.get("url", "http://localhost:4646")
        if not url:
            raise ValueError("nomad collector: 'url' must not be empty")
        pattern = self._config.get("job_pattern")
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"nomad collector: invalid job_pattern '{pattern}': {exc}"
                ) from exc

    def collect(self) -> ConfigSnapshot:
        headers: dict[str, str] = {}
        if self._token:
            headers["X-Nomad-Token"] = self._token

        resp = requests.get(
            f"{self._url}/v1/jobs",
            params={"namespace": self._namespace},
            headers=headers,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        jobs: list[dict[str, Any]] = resp.json()

        data: dict[str, Any] = {}
        for job in jobs:
            job_id: str = job.get("ID", "")
            if self._job_pattern and not self._job_pattern.search(job_id):
                continue
            data[job_id] = {
                "status": job.get("Status"),
                "type": job.get("Type"),
                "namespace": job.get("Namespace", self._namespace),
            }

        return ConfigSnapshot(source=f"nomad:{self._url}", data=data)
