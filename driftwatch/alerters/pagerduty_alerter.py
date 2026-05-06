"""PagerDuty Events API v2 alerter."""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from driftwatch.detectors.drift_detector import DriftEvent

_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"


class PagerDutyAlerter:
    """Emit drift events to PagerDuty via the Events API v2."""

    def __init__(self, config: dict[str, Any]) -> None:
        routing_key: str = config.get("routing_key", "")
        if not routing_key:
            raise ValueError("PagerDutyAlerter requires a non-empty 'routing_key'")
        self._routing_key = routing_key
        self._severity: str = config.get("severity", "warning")
        self._source: str = config.get("source", "driftwatch")
        self._timeout: int = int(config.get("timeout", 10))

    def _build_payload(self, event: DriftEvent) -> dict[str, Any]:
        return {
            "routing_key": self._routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": (
                    f"Drift detected: {event.key} {event.change_type} "
                    f"in {event.collector}"
                ),
                "source": self._source,
                "severity": self._severity,
                "custom_details": event.to_dict(),
            },
        }

    def _post(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            _EVENTS_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
            if resp.status not in (200, 202):
                raise RuntimeError(
                    f"PagerDuty returned unexpected status {resp.status}"
                )

    def emit(self, events: list[DriftEvent]) -> None:
        for event in events:
            self._post(self._build_payload(event))

    def emit_summary(self, events: list[DriftEvent]) -> None:
        """PagerDuty triggers one alert per event; summary delegates to emit."""
        self.emit(events)
