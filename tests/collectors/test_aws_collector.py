"""Tests for AwsCollector."""
from __future__ import annotations

import sys
from types import ModuleType
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.aws_collector import AwsCollector


def _make_param(name: str, value: str) -> Dict[str, str]:
    return {"Name": name, "Value": value, "Type": "String"}


def _stub_boto3(params: List[Dict[str, str]]):
    """Return a mock boto3 module whose SSM client yields *params*."""
    page = {"Parameters": params}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]

    client = MagicMock()
    client.get_paginator.return_value = paginator
    client.get_parameters.return_value = {"Parameters": params}

    boto3_mod = MagicMock()
    boto3_mod.client.return_value = client
    return boto3_mod, client


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_config_ok_with_path_prefix():
    c = AwsCollector({"path_prefix": "/app"})
    c.validate_config()  # should not raise


def test_validate_config_ok_with_parameters():
    c = AwsCollector({"parameters": ["/app/db_host"]})
    c.validate_config()


def test_validate_config_missing_both_raises():
    c = AwsCollector({"path_prefix": "", "parameters": []})
    with pytest.raises(ValueError, match="path_prefix.*parameters"):
        c.validate_config()


def test_validate_config_bad_pattern_raises():
    c = AwsCollector({"path_prefix": "/app", "pattern": "[invalid"})
    with pytest.raises(ValueError, match="invalid pattern"):
        c.validate_config()


# ---------------------------------------------------------------------------
# collect — path_prefix mode
# ---------------------------------------------------------------------------

def test_collect_path_prefix_returns_all(monkeypatch):
    params = [_make_param("/app/host", "db.local"), _make_param("/app/port", "5432")]
    boto3_mod, _ = _stub_boto3(params)
    monkeypatch.setitem(sys.modules, "boto3", boto3_mod)

    snap = AwsCollector({"path_prefix": "/app"}).collect()
    assert snap.data == {"/app/host": "db.local", "/app/port": "5432"}
    assert snap.source == "aws"


def test_collect_path_prefix_with_pattern_filters(monkeypatch):
    params = [_make_param("/app/host", "db.local"), _make_param("/app/debug", "true")]
    boto3_mod, _ = _stub_boto3(params)
    monkeypatch.setitem(sys.modules, "boto3", boto3_mod)

    snap = AwsCollector({"path_prefix": "/app", "pattern": r"host"}).collect()
    assert list(snap.data.keys()) == ["/app/host"]


# ---------------------------------------------------------------------------
# collect — explicit parameters mode
# ---------------------------------------------------------------------------

def test_collect_explicit_parameters(monkeypatch):
    params = [_make_param("/app/secret", "s3cr3t")]
    boto3_mod, client = _stub_boto3(params)
    monkeypatch.setitem(sys.modules, "boto3", boto3_mod)

    snap = AwsCollector({"parameters": ["/app/secret"]}).collect()
    assert snap.data == {"/app/secret": "s3cr3t"}
    client.get_parameters.assert_called_once_with(
        Names=["/app/secret"], WithDecryption=True
    )


def test_collect_uses_configured_region(monkeypatch):
    boto3_mod, _ = _stub_boto3([])
    monkeypatch.setitem(sys.modules, "boto3", boto3_mod)

    AwsCollector({"path_prefix": "/x", "region": "eu-west-1"}).collect()
    boto3_mod.client.assert_called_once_with("ssm", region_name="eu-west-1")
