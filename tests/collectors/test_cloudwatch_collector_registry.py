"""Registry integration tests for CloudWatchCollector."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from driftwatch.collectors import get_collector, list_collectors


def _make_response(alarms: list) -> MagicMock:
    paginator = MagicMock()
    paginator.paginate.return_value = [{"MetricAlarms": alarms}]
    client = MagicMock()
    client.get_paginator.return_value = paginator
    session = MagicMock()
    session.client.return_value = client
    mock_boto3 = MagicMock()
    mock_boto3.Session.return_value = session
    return mock_boto3


def test_cloudwatch_in_list_collectors():
    assert "cloudwatch" in list_collectors()


def test_get_collector_returns_cloudwatch_instance():
    from driftwatch.collectors.cloudwatch_collector import CloudWatchCollector
    c = get_collector("cloudwatch", {"region": "eu-west-1"})
    assert isinstance(c, CloudWatchCollector)


def test_get_collector_cloudwatch_invalid_pattern_raises():
    with pytest.raises(ValueError, match="invalid alarm_pattern"):
        get_collector("cloudwatch", {"region": "us-east-1", "alarm_pattern": "[bad"})


def test_get_collector_cloudwatch_collect_via_registry(monkeypatch):
    mock_boto3 = _make_response([
        {"AlarmName": "test-alarm", "StateValue": "OK",
         "MetricName": "CPUUtilization", "Namespace": "AWS/EC2",
         "StateReason": "Threshold crossed"}
    ])
    monkeypatch.setattr("driftwatch.collectors.cloudwatch_collector.boto3", mock_boto3)
    c = get_collector("cloudwatch", {"region": "us-east-1"})
    snap = c.collect()
    assert "test-alarm" in snap.data
    assert snap.data["test-alarm"]["state"] == "OK"
