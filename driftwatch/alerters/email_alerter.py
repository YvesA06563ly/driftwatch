"""Email alerter — sends drift events via SMTP."""

from __future__ import annotations

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from driftwatch.detectors.drift_detector import DriftEvent


class EmailAlerter:
    """Sends drift alerts as plain-text/JSON emails over SMTP."""

    def __init__(self, config: dict) -> None:
        host = config.get("smtp_host", "").strip()
        if not host:
            raise ValueError("email alerter requires 'smtp_host'")
        to_addrs = config.get("to", [])
        if not to_addrs:
            raise ValueError("email alerter requires at least one 'to' address")
        from_addr = config.get("from", "").strip()
        if not from_addr:
            raise ValueError("email alerter requires a 'from' address")

        self._host = host
        self._port = int(config.get("port", 587))
        self._username = config.get("username", "")
        self._password = config.get("password", "")
        self._use_tls = bool(config.get("use_tls", True))
        self._from = from_addr
        self._to = list(to_addrs)
        self._subject_prefix = config.get("subject_prefix", "[DriftWatch]")

    # ------------------------------------------------------------------
    def _send(self, subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = ", ".join(self._to)
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self._host, self._port) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username:
                smtp.login(self._username, self._password)
            smtp.sendmail(self._from, self._to, msg.as_string())

    # ------------------------------------------------------------------
    def emit(self, events: List[DriftEvent]) -> None:
        """Send one email per drift event."""
        for event in events:
            subject = f"{self._subject_prefix} Drift detected: {event.key} [{event.change_type}]"
            body = json.dumps(event.to_dict(), indent=2)
            self._send(subject, body)

    def emit_summary(self, events: List[DriftEvent]) -> None:
        """Send a single summary email for all events."""
        if not events:
            return
        subject = f"{self._subject_prefix} {len(events)} drift event(s) detected"
        lines = [f"Total events: {len(events)}", ""]
        for ev in events:
            lines.append(json.dumps(ev.to_dict(), indent=2))
            lines.append("")
        self._send(subject, "\n".join(lines))
