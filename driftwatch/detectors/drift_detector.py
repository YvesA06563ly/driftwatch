"""Drift detector: compares two ConfigSnapshots and emits structured drift events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from driftwatch.collectors.base import ConfigSnapshot


@dataclass
class DriftEvent:
    """Represents a single detected drift between two snapshots."""

    collector: str
    key: str
    kind: str  # 'added' | 'removed' | 'changed'
    previous: Any
    current: Any
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "collector": self.collector,
            "key": self.key,
            "kind": self.kind,
            "previous": self.previous,
            "current": self.current,
            "detected_at": self.detected_at,
        }


class DriftDetector:
    """Compares a baseline snapshot against a current snapshot and returns drift events."""

    def __init__(self, collector_name: str) -> None:
        self.collector_name = collector_name

    def compare(
        self,
        baseline: ConfigSnapshot,
        current: ConfigSnapshot,
    ) -> list[DriftEvent]:
        """Return a list of DriftEvents describing differences between snapshots."""
        events: list[DriftEvent] = []
        baseline_data = baseline.data
        current_data = current.data

        all_keys = set(baseline_data) | set(current_data)

        for key in sorted(all_keys):
            in_baseline = key in baseline_data
            in_current = key in current_data

            if in_baseline and not in_current:
                events.append(
                    DriftEvent(
                        collector=self.collector_name,
                        key=key,
                        kind="removed",
                        previous=baseline_data[key],
                        current=None,
                    )
                )
            elif not in_baseline and in_current:
                events.append(
                    DriftEvent(
                        collector=self.collector_name,
                        key=key,
                        kind="added",
                        previous=None,
                        current=current_data[key],
                    )
                )
            elif baseline_data[key] != current_data[key]:
                events.append(
                    DriftEvent(
                        collector=self.collector_name,
                        key=key,
                        kind="changed",
                        previous=baseline_data[key],
                        current=current_data[key],
                    )
                )

        return events
