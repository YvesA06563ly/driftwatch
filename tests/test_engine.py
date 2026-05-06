"""Tests for driftwatch.engine.Engine."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.base import ConfigSnapshot
from driftwatch.detectors.drift_detector import DriftEvent
from driftwatch.engine import Engine


def _make_snapshot(data: dict) -> ConfigSnapshot:
    return ConfigSnapshot(source="test", data=data)


@pytest.fixture()
def minimal_config():
    return {
        "collectors": [{"type": "env", "options": {"prefix": "DRIFTWATCH_TEST_"}}],
        "alerters": [],
    }


def test_capture_baseline_populates_baseline(minimal_config):
    engine = Engine(minimal_config)
    assert engine._baseline == {}
    engine.capture_baseline()
    assert len(engine._baseline) == 1


def test_run_cycle_without_baseline_captures_and_returns_empty(minimal_config):
    engine = Engine(minimal_config)
    events = engine.run_cycle()
    assert events == []
    assert len(engine._baseline) == 1


def test_run_cycle_detects_no_drift_when_state_unchanged(minimal_config):
    engine = Engine(minimal_config)
    engine.capture_baseline()
    events = engine.run_cycle()
    assert events == []


def test_run_cycle_detects_drift_and_calls_alerters():
    snap_a = _make_snapshot({"KEY": "old"})
    snap_b = _make_snapshot({"KEY": "new"})

    mock_collector = MagicMock()
    mock_collector.name = "mock"
    mock_collector.collect.side_effect = [snap_a, snap_b]

    mock_alerter = MagicMock()

    engine = Engine({"collectors": [], "alerters": []})
    engine._collectors = [mock_collector]
    engine._alerters = [mock_alerter]

    engine.capture_baseline()
    events = engine.run_cycle()

    assert len(events) == 1
    assert events[0].key == "KEY"
    mock_alerter.emit.assert_called_once_with(events)


def test_run_cycle_updates_baseline_after_cycle():
    snap_a = _make_snapshot({"X": "1"})
    snap_b = _make_snapshot({"X": "2"})
    snap_c = _make_snapshot({"X": "2"})

    mock_collector = MagicMock()
    mock_collector.name = "mc"
    mock_collector.collect.side_effect = [snap_a, snap_b, snap_c]

    engine = Engine({"collectors": [], "alerters": []})
    engine._collectors = [mock_collector]

    engine.capture_baseline()
    engine.run_cycle()          # drift: 1 -> 2
    events = engine.run_cycle() # no drift: 2 -> 2
    assert events == []
