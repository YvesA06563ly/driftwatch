"""Webhook alerter — POSTs structured drift events to an HTTP endpoint."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from driftwatch.detectors.drift_detector import DriftEvent

logger = logging.getLogger(__name__)


class WebhookAlerter:
    """Sends drift events as JSON payloads to a configurable webhook URL."""

    def __init__(
        self,
        url: str,
        *,
        timeout: int = 10,
        headers: Optional[Dict[str, str]] = None,
        include_summary: bool = True,
    ) -> None:
        if not url:
            raise ValueError("WebhookAlerter requires a non-empty 'url'")
        self.url = url
        self.timeout = timeout
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            **(headers or {}),
        }
        self.include_summary = include_summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, payload: Dict[str, Any]) -> int:
        """Serialize *payload* and POST it; return the HTTP status code."""
        data = json.dumps(payload, default=str).encode()
        req = urllib.request.Request(self.url, data=data, headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            logger.error("Webhook HTTP error %s for %s", exc.code, self.url)
            return exc.code
        except urllib.error.URLError as exc:
            logger.error("Webhook request failed: %s", exc.reason)
            return 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(self, events: List[DriftEvent]) -> None:
        """POST each drift event individually to the webhook endpoint."""
        for event in events:
            payload = event.to_dict()
            status = self._post(payload)
            if status and 200 <= status < 300:
                logger.debug("Webhook accepted event '%s' (%s)", event.key, status)
            else:
                logger.warning("Webhook rejected event '%s': status=%s", event.key, status)

    def emit_summary(self, events: List[DriftEvent]) -> None:
        """POST all drift events as a single batched summary payload."""
        if not events or not self.include_summary:
            return
        payload = {
            "event_type": "drift_summary",
            "total": len(events),
            "events": [e.to_dict() for e in events],
        }
        status = self._post(payload)
        if status and 200 <= status < 300:
            logger.debug("Webhook summary accepted (%s events, status=%s)", len(events), status)
        else:
            logger.warning("Webhook summary rejected: status=%s", status)
