"""Tests for LogAlerter."""

import io
import json

import pytest

from driftwatch.alerters.log_alerter import LogAlerter
from driftwatch.detectors.drift_detector import DriftEvent


@pytest.fixture
def buf():
    return io.StringIO()


@pytest.fixture
def alerter(buf):
    return LogAlerter(level="warning", output=buf, include_timestamp=False)


def _make_event(change_type="changed", key="KEY", old=None, new="new"):
    return DriftEvent(collector="test_col", key=key, change_type=change_type, old_value=old, new_value=new)


def test_emit_no_events_writes_nothing(alerter, buf):
    alerter.emit([])
    assert buf.getvalue() == ""


def test_emit_single_event_valid_json(alerter, buf):
    alerter.emit([_make_event()])
    line = buf.getvalue().strip()
    record = json.loads(line)
    assert record["alert"] == "drift_detected"
    assert record["collector"] == "test_col"
    assert record["key"] == "KEY"
    assert record["change_type"] == "changed"
    assert record["new_value"] == "new"


def test_emit_multiple_events_multiple_lines(alerter, buf):
    events = [_make_event(key=f"K{i}") for i in range(3)]
    alerter.emit(events)
    lines = [l for l in buf.getvalue().strip().splitlines() if l]
    assert len(lines) == 3
    for line in lines:
        assert json.loads(line)["alert"] == "drift_detected"


def test_emit_includes_timestamp_when_enabled(buf):
    alerter = LogAlerter(output=buf, include_timestamp=True)
    alerter.emit([_make_event()])
    record = json.loads(buf.getvalue().strip())
    assert "timestamp" in record


def test_emit_excludes_timestamp_when_disabled(alerter, buf):
    alerter.emit([_make_event()])
    record = json.loads(buf.getvalue().strip())
    assert "timestamp" not in record


def test_emit_summary_correct_counts(buf):
    alerter = LogAlerter(output=buf, include_timestamp=False)
    events = [
        _make_event(change_type="added", key="A"),
        _make_event(change_type="added", key="B"),
        _make_event(change_type="removed", key="C"),
    ]
    alerter.emit_summary(events)
    record = json.loads(buf.getvalue().strip())
    assert record["alert"] == "drift_summary"
    assert record["total_changes"] == 3
    assert record["change_types"]["added"] == 2
    assert record["change_types"]["removed"] == 1


def test_emit_summary_no_events_writes_nothing(alerter, buf):
    alerter.emit_summary([])
    assert buf.getvalue() == ""


def test_emit_summary_includes_timestamp_when_enabled(buf):
    """Verify emit_summary also respects the include_timestamp flag."""
    alerter = LogAlerter(output=buf, include_timestamp=True)
    alerter.emit_summary([_make_event(change_type="added", key="A")])
    record = json.loads(buf.getvalue().strip())
    assert "timestamp" in record


def test_invalid_level_raises():
    with pytest.raises(ValueError, match="Unsupported log level"):
        LogAlerter(level="verbose")


def test_pretty_output_is_multiline(buf):
    alerter = LogAlerter(output=buf, include_timestamp=False, pretty=True)
    alerter.emit([_make_event()])
    output = buf.getvalue()
    assert "\n" in output
    json.loads(output)  # still valid JSON
