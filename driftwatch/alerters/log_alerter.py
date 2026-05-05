"""Log-based alerter that emits structured drift alerts to stdout/stderr or a file."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import IO, List, Optional

from driftwatch.detectors.drift_detector import DriftEvent

logger = logging.getLogger(__name__)


class LogAlerter:
    """Emits DriftEvents as structured JSON log lines."""

    SUPPORTED_LEVELS = {"info", "warning", "error", "critical"}

    def __init__(
        self,
        level: str = "warning",
        output: Optional[IO] = None,
        include_timestamp: bool = True,
        pretty: bool = False,
    ) -> None:
        level = level.lower()
        if level not in self.SUPPORTED_LEVELS:
            raise ValueError(
                f"Unsupported log level '{level}'. Choose from {self.SUPPORTED_LEVELS}"
            )
        self.level = level
        self.output = output or sys.stdout
        self.include_timestamp = include_timestamp
        self.pretty = pretty

    def _build_record(self, event: DriftEvent) -> dict:
        record = {
            "alert": "drift_detected",
            "collector": event.collector,
            "key": event.key,
            "change_type": event.change_type,
            "old_value": event.old_value,
            "new_value": event.new_value,
        }
        if self.include_timestamp:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
        return record

    def emit(self, events: List[DriftEvent]) -> None:
        """Emit all drift events as structured JSON lines."""
        if not events:
            return
        indent = 2 if self.pretty else None
        for event in events:
            record = self._build_record(event)
            line = json.dumps(record, indent=indent)
            print(line, file=self.output)
            getattr(logger, self.level)("drift detected: %s.%s [%s]", event.collector, event.key, event.change_type)

    def emit_summary(self, events: List[DriftEvent]) -> None:
        """Emit a single summary record for a batch of drift events."""
        if not events:
            return
        summary = {
            "alert": "drift_summary",
            "total_changes": len(events),
            "collectors": list({e.collector for e in events}),
            "change_types": {ct: sum(1 for e in events if e.change_type == ct) for ct in {e.change_type for e in events}},
        }
        if self.include_timestamp:
            summary["timestamp"] = datetime.now(timezone.utc).isoformat()
        indent = 2 if self.pretty else None
        print(json.dumps(summary, indent=indent), file=self.output)
