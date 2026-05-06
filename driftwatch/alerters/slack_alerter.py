"""Slack webhook alerter — posts drift events as Slack messages."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import urllib.request
import urllib.error

from driftwatch.detectors.drift_detector import DriftEvent

log = logging.getLogger(__name__)


class SlackAlerter:
    """Emit drift events to a Slack incoming-webhook URL."""

    def __init__(self, config: Dict[str, Any]) -> None:
        webhook_url: str = config.get("webhook_url", "").strip()
        if not webhook_url:
            raise ValueError("SlackAlerter requires a non-empty 'webhook_url'")
        if not webhook_url.startswith("https://"):
            raise ValueError("SlackAlerter 'webhook_url' must start with 'https://'")
        self._url = webhook_url
        self._username: str = config.get("username", "DriftWatch")
        self._icon_emoji: str = config.get("icon_emoji", ":warning:")
        self._timeout: int = int(config.get("timeout", 10))

    def _build_payload(self, events: List[DriftEvent]) -> Dict[str, Any]:
        lines = []
        for ev in events:
            lines.append(
                f"• *{ev.key}* [{ev.change_type}] "
                f"collector=`{ev.collector}` "
                f"old=`{ev.old_value}` → new=`{ev.new_value}`"
            )
        text = "\n".join(lines) or "_No drift detected._"
        return {
            "username": self._username,
            "icon_emoji": self._icon_emoji,
            "text": f":rotating_light: *DriftWatch alert* — {len(events)} event(s)\n{text}",
        }

    def _post(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            self._url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            log.error("SlackAlerter HTTP error: %s", exc)
        except urllib.error.URLError as exc:
            log.error("SlackAlerter URL error: %s", exc)
            return
        if status != 200:
            log.warning("SlackAlerter unexpected status: %d", status)
        else:
            log.debug("SlackAlerter posted %d event(s)", len(payload))

    def emit(self, events: List[DriftEvent]) -> None:
        if not events:
            return
        self._post(self._build_payload(events))

    def emit_summary(self, events: List[DriftEvent]) -> None:
        self._post(self._build_payload(events))
