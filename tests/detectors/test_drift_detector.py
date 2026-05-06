"""Tests for DriftDetector."""

import pytest

from driftwatch.collectors.base import ConfigSnapshot
from driftwatch.detectors.drift_detector import DriftDetector, DriftEvent


COLLECTOR_NAME = "test_collector"


@pytest.fixture
def detector() -> DriftDetector:
    return DriftDetector(collector_name=COLLECTOR_NAME)


def _snap(data: dict) -> ConfigSnapshot:
    return ConfigSnapshot(collector=COLLECTOR_NAME, data=data)


def test_no_drift_returns_empty_list(detector):
    baseline = _snap({"KEY": "value", "PORT": "8080"})
    current = _snap({"KEY": "value", "PORT": "8080"})
    events = detector.compare(baseline, current)
    assert events == []


def test_detects_added_key(detector):
    baseline = _snap({"KEY": "value"})
    current = _snap({"KEY": "value", "NEW_KEY": "new"})
    events = detector.compare(baseline, current)
    assert len(events) == 1
    e = events[0]
    assert e.kind == "added"
    assert e.key == "NEW_KEY"
    assert e.previous is None
    assert e.current == "new"
    assert e.collector == COLLECTOR_NAME


def test_detects_removed_key(detector):
    baseline = _snap({"KEY": "value", "OLD_KEY": "old"})
    current = _snap({"KEY": "value"})
    events = detector.compare(baseline, current)
    assert len(events) == 1
    e = events[0]
    assert e.kind == "removed"
    assert e.key == "OLD_KEY"
    assert e.previous == "old"
    assert e.current is None


def test_detects_changed_key(detector):
    baseline = _snap({"KEY": "old_value"})
    current = _snap({"KEY": "new_value"})
    events = detector.compare(baseline, current)
    assert len(events) == 1
    e = events[0]
    assert e.kind == "changed"
    assert e.key == "KEY"
    assert e.previous == "old_value"
    assert e.current == "new_value"


def test_detects_multiple_drift_types(detector):
    baseline = _snap({"A": "1", "B": "2", "C": "3"})
    current = _snap({"A": "1", "B": "changed", "D": "4"})
    events = detector.compare(baseline, current)
    kinds = {e.kind for e in events}
    assert "removed" in kinds  # C removed
    assert "changed" in kinds  # B changed
    assert "added" in kinds    # D added
    assert len(events) == 3


def test_to_dict_structure(detector):
    baseline = _snap({"KEY": "old"})
    current = _snap({"KEY": "new"})
    events = detector.compare(baseline, current)
    assert len(events) == 1
    d = events[0].to_dict()
    assert set(d.keys()) == {"collector", "key", "kind", "previous", "current", "detected_at"}
    assert d["kind"] == "changed"
    assert "T" in d["detected_at"]  # ISO 8601 format


def test_empty_snapshots_no_drift(detector):
    events = detector.compare(_snap({}), _snap({}))
    assert events == []


def test_both_empty_to_populated(detector):
    events = detector.compare(_snap({}), _snap({"X": "1"}))
    assert len(events) == 1
    assert events[0].kind == "added"


def test_collector_name_propagated_to_all_events(detector):
    """All drift events should carry the collector name from the detector."""
    baseline = _snap({"A": "1", "B": "2"})
    current = _snap({"A": "changed", "C": "3"})
    events = detector.compare(baseline, current)
    # Expect: A changed, B removed, C added
    assert len(events) == 3
    for event in events:
        assert event.collector == COLLECTOR_NAME
