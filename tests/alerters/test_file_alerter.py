"""Tests for FileAlerter."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from driftwatch.alerters.file_alerter import FileAlerter
from driftwatch.detectors.drift_detector import DriftEvent


@pytest.fixture()
def alert_file(tmp_path):
    return str(tmp_path / "alerts" / "drift.jsonl")


@pytest.fixture()
def alerter(alert_file):
    return FileAlerter(path=alert_file)


def _make_event(key="cfg.timeout", kind="changed", old="30", new="60"):
    return DriftEvent(
        collector="test",
        key=key,
        kind=kind,
        old_value=old,
        new_value=new,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _read_lines(path: str):
    with open(path, encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def test_empty_path_raises():
    with pytest.raises(ValueError, match="non-empty"):
        FileAlerter(path="")


def test_creates_parent_directories(tmp_path):
    nested = str(tmp_path / "a" / "b" / "c" / "drift.jsonl")
    FileAlerter(path=nested)
    assert os.path.isdir(os.path.dirname(nested))


def test_emit_no_events_writes_nothing(alerter, alert_file):
    alerter.emit([])
    assert not os.path.exists(alert_file) or _read_lines(alert_file) == []


def test_emit_single_event_valid_json(alerter, alert_file):
    alerter.emit([_make_event()])
    lines = _read_lines(alert_file)
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["key"] == "cfg.timeout"
    assert record["kind"] == "changed"


def test_emit_multiple_events_each_on_own_line(alerter, alert_file):
    alerter.emit([_make_event("a"), _make_event("b"), _make_event("c")])
    lines = _read_lines(alert_file)
    assert len(lines) == 3
    keys = [json.loads(l)["key"] for l in lines]
    assert keys == ["a", "b", "c"]


def test_emit_summary_contains_summary_type(alerter, alert_file):
    alerter.emit_summary([_make_event()], collector_name="env")
    lines = _read_lines(alert_file)
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["type"] == "summary"
    assert record["collector"] == "env"
    assert record["total_drift_events"] == 1


def test_emit_summary_empty_events(alerter, alert_file):
    alerter.emit_summary([], collector_name="files")
    lines = _read_lines(alert_file)
    record = json.loads(lines[0])
    assert record["total_drift_events"] == 0
    assert record["events"] == []


def test_emit_appends_across_calls(alerter, alert_file):
    alerter.emit([_make_event("x")])
    alerter.emit([_make_event("y")])
    lines = _read_lines(alert_file)
    assert len(lines) == 2
