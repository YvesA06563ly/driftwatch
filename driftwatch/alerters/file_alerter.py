"""File-based alerter: appends structured JSON alerts to a rotating log file."""

from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import List, Optional

from driftwatch.detectors.drift_detector import DriftEvent


class FileAlerter:
    """Writes drift events as newline-delimited JSON to a rotating file."""

    def __init__(
        self,
        path: str,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 3,
        encoding: str = "utf-8",
    ) -> None:
        if not path:
            raise ValueError("FileAlerter requires a non-empty 'path'")

        self.path = path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.encoding = encoding

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        self._logger = logging.getLogger(f"driftwatch.file_alerter.{path}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = RotatingFileHandler(
                path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding=encoding,
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def emit(self, events: List[DriftEvent]) -> None:
        """Append each event as a JSON line to the alert file."""
        for event in events:
            line = json.dumps(event.to_dict(), default=str)
            self._logger.info(line)

    def emit_summary(self, events: List[DriftEvent], collector_name: Optional[str] = None) -> None:
        """Append a summary record containing all events for a single cycle."""
        summary = {
            "type": "summary",
            "collector": collector_name,
            "total_drift_events": len(events),
            "events": [e.to_dict() for e in events],
        }
        self._logger.info(json.dumps(summary, default=str))
