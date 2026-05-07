"""Registry integration tests for AwsCollector."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from driftwatch.collectors import get_collector, list_collectors


def test_aws_in_list_collectors():
    assert "aws" in list_collectors()


def test_get_collector_returns_aws_instance():
    from driftwatch.collectors.aws_collector import AwsCollector

    collector = get_collector("aws", {"path_prefix": "/app"})
    assert isinstance(collector, AwsCollector)


def test_get_collector_aws_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("aws", {"path_prefix": "", "parameters": []})


def test_get_collector_aws_collect_via_registry(monkeypatch):
    page = {"Parameters": [{"Name": "/svc/key", "Value": "val"}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    client = MagicMock()
    client.get_paginator.return_value = paginator
    boto3_mod = MagicMock()
    boto3_mod.client.return_value = client
    monkeypatch.setitem(sys.modules, "boto3", boto3_mod)

    collector = get_collector("aws", {"path_prefix": "/svc"})
    snap = collector.collect()
    assert snap.data == {"/svc/key": "val"}
