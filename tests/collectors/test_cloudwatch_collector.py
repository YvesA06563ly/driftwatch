"""Tests for CloudWatchCollector."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from driftwatch.collectors.cloudwatch_collector import CloudWatchCollector


def _make_alarm(name: str, state: str, metric: str = "CPUUtilization") -> dict:
    return {
        "AlarmName": name,
        "StateValue": state,
        "MetricName": metric,
        "Namespace": "AWS/EC2",
        "StateReason": f"{name} reason",
    }


def _make_collector(extra: dict | None = None) -> CloudWatchCollector:
    cfg = {"region": "us-west-2", **(extra or {})}
    c = CloudWatchCollector(cfg)
    c.validate_config()
    return c


@pytest.fixture()
def patched_cw(monkeypatch):
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client
    mock_boto3 = MagicMock()
    mock_boto3.Session.return_value = mock_session
    monkeypatch.setattr("driftwatch.collectors.cloudwatch_collector.boto3", mock_boto3)
    return mock_client


def _set_pages(client, alarms: list) -> None:
    paginator = MagicMock()
    paginator.paginate.return_value = [{"MetricAlarms": alarms}]
    client.get_paginator.return_value = paginator


def test_validate_config_ok():
    _make_collector()  # should not raise


def test_validate_config_bad_pattern_raises():
    with pytest.raises(ValueError, match="invalid alarm_pattern"):
        _make_collector({"alarm_pattern": "[invalid"})


def test_validate_config_bad_state_filter_raises():
    with pytest.raises(ValueError, match="invalid state_filter"):
        _make_collector({"state_filter": ["UNKNOWN"]})


def test_collect_returns_all_alarms(patched_cw):
    alarms = [
        _make_alarm("alarm-a", "OK"),
        _make_alarm("alarm-b", "ALARM"),
    ]
    _set_pages(patched_cw, alarms)
    snap = _make_collector().collect()
    assert "alarm-a" in snap.data
    assert "alarm-b" in snap.data
    assert snap.data["alarm-a"]["state"] == "OK"


def test_collect_with_pattern_filters(patched_cw):
    alarms = [
        _make_alarm("prod-cpu", "ALARM"),
        _make_alarm("dev-cpu", "OK"),
    ]
    _set_pages(patched_cw, alarms)
    snap = _make_collector({"alarm_pattern": r"^prod-"}).collect()
    assert "prod-cpu" in snap.data
    assert "dev-cpu" not in snap.data


def test_collect_with_state_filter(patched_cw):
    alarms = [
        _make_alarm("alarm-a", "OK"),
        _make_alarm("alarm-b", "ALARM"),
    ]
    _set_pages(patched_cw, alarms)
    snap = _make_collector({"state_filter": ["ALARM"]}).collect()
    assert "alarm-b" in snap.data
    assert "alarm-a" not in snap.data


def test_collect_snapshot_source(patched_cw):
    _set_pages(patched_cw, [])
    snap = _make_collector().collect()
    assert snap.source == "cloudwatch"


def test_collect_alarm_fields(patched_cw):
    _set_pages(patched_cw, [_make_alarm("my-alarm", "ALARM", "DiskReadOps")])
    snap = _make_collector().collect()
    entry = snap.data["my-alarm"]
    assert entry["metric"] == "DiskReadOps"
    assert entry["namespace"] == "AWS/EC2"
    assert "reason" in entry
