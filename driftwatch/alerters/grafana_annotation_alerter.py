"""Alerter that posts drift events as Grafana annotations."""
from __future__ import annotations

from typing import Any

import requests

from driftwatch.alerters.base import BaseAlerter  # type: ignore[import]
from driftwatch.detectors.drift_detector import DriftEvent


class GrafanaAnnotationAlerter:
    """Post each drift event as a Grafana annotation on a given dashboard."""

    name = "grafana_annotation"

    def __init__(self, config: dict[str, Any]) -> None:
        self._url: str = config.get("url", "").rstrip("/")
        self._api_key: str = config.get("api_key", "")
        self._dashboard_id: int | None = config.get("dashboard_id")
        self._panel_id: int | None = config.get("panel_id")
        self._tags: list[str] = config.get("tags", ["driftwatch"])
        self._timeout: int = int(config.get("timeout", 10))

        if not self._url:
            raise ValueError("grafana_annotation alerter requires a non-empty 'url'")
        if not self._url.startswith(("http://", "https://")):
            raise ValueError("grafana_annotation 'url' must start with http:// or https://")
        if not self._api_key:
            raise ValueError("grafana_annotation alerter requires a non-empty 'api_key'")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _build_payload(self, event: DriftEvent) -> dict[str, Any]:
        text = f"[{event.change_type}] {event.key}: {event.old_value!r} → {event.new_value!r}"
        payload: dict[str, Any] = {
            "text": text,
            "tags": self._tags,
        }
        if self._dashboard_id is not None:
            payload["dashboardId"] = self._dashboard_id
        if self._panel_id is not None:
            payload["panelId"] = self._panel_id
        return payload

    def _post(self, payload: dict[str, Any]) -> None:
        resp = requests.post(
            f"{self._url}/api/annotations",
            json=payload,
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()

    def emit(self, events: list[DriftEvent]) -> None:
        for event in events:
            self._post(self._build_payload(event))

    def emit_summary(self, events: list[DriftEvent]) -> None:
        if not events:
            return
        summary = f"Drift detected: {len(events)} change(s)"
        payload: dict[str, Any] = {"text": summary, "tags": self._tags}
        if self._dashboard_id is not None:
            payload["dashboardId"] = self._dashboard_id
        self._post(payload)
