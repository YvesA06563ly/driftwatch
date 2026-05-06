"""DriftWatch engine: orchestrates collectors, detector, and alerters."""
from __future__ import annotations

import logging
from typing import Any

from driftwatch.collectors import get_collector
from driftwatch.collectors.base import BaseCollector, ConfigSnapshot
from driftwatch.detectors.drift_detector import DriftDetector, DriftEvent

logger = logging.getLogger(__name__)


class Engine:
    """Runs one drift-detection cycle and returns detected events."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._detector = DriftDetector()
        self._alerters: list[Any] = []
        self._collectors: list[BaseCollector] = []
        self._baseline: dict[str, ConfigSnapshot] = {}
        self._build_collectors()
        self._build_alerters()

    # ------------------------------------------------------------------
    def _build_collectors(self) -> None:
        for entry in self._config.get("collectors", []):
            collector = get_collector(entry["type"], entry.get("options", {}))
            self._collectors.append(collector)

    def _build_alerters(self) -> None:
        from driftwatch.alerters.log_alerter import LogAlerter
        from driftwatch.alerters.webhook_alerter import WebhookAlerter

        for entry in self._config.get("alerters", []):
            kind = entry["type"]
            opts = entry.get("options", {})
            if kind == "log":
                self._alerters.append(LogAlerter(**opts))
            elif kind == "webhook":
                self._alerters.append(WebhookAlerter(**opts))
            else:
                logger.warning("Unknown alerter type: %s", kind)

    # ------------------------------------------------------------------
    def capture_baseline(self) -> None:
        """Collect current state and store it as the baseline."""
        self._baseline = {}
        for collector in self._collectors:
            snapshot = collector.collect()
            self._baseline[collector.name] = snapshot
        logger.info("Baseline captured for %d collectors.", len(self._baseline))

    def run_cycle(self) -> list[DriftEvent]:
        """Collect current state, compare with baseline, emit alerts."""
        if not self._baseline:
            logger.warning("No baseline found; capturing now.")
            self.capture_baseline()
            return []

        all_events: list[DriftEvent] = []
        for collector in self._collectors:
            current = collector.collect()
            previous = self._baseline.get(collector.name)
            if previous is None:
                logger.warning("No baseline for collector %s; skipping.", collector.name)
                continue
            events = self._detector.compare(previous, current)
            all_events.extend(events)
            self._baseline[collector.name] = current

        for alerter in self._alerters:
            alerter.emit(all_events)

        return all_events
