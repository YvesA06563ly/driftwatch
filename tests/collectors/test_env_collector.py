"""Tests for the EnvCollector and ConfigSnapshot."""

import os
from datetime import datetime
from unittest.mock import patch

import pytest

from driftwatch.collectors.base import ConfigSnapshot
from driftwatch.collectors.env_collector import EnvCollector

SAMPLE_ENV = {
    "APP_HOST": "localhost",
    "APP_PORT": "8080",
    "DB_URL": "postgres://localhost/mydb",
    "SECRET_KEY": "supersecret",
    "HOME": "/home/user",
}


@pytest.fixture()
def patched_env():
    with patch.dict(os.environ, SAMPLE_ENV, clear=True):
        yield


def test_collect_with_prefix(patched_env):
    collector = EnvCollector(config={"prefix": "APP_"})
    snapshots = collector.collect()
    keys = {s.key for s in snapshots}
    assert keys == {"APP_HOST", "APP_PORT"}


def test_collect_with_pattern(patched_env):
    collector = EnvCollector(config={"pattern": r"^(APP|DB)_.*"})
    snapshots = collector.collect()
    keys = {s.key for s in snapshots}
    assert keys == {"APP_HOST", "APP_PORT", "DB_URL"}


def test_collect_with_exclude(patched_env):
    collector = EnvCollector(config={"prefix": "APP_", "exclude": ["APP_PORT"]})
    snapshots = collector.collect()
    keys = {s.key for s in snapshots}
    assert "APP_PORT" not in keys
    assert "APP_HOST" in keys


def test_collect_no_filter_returns_all(patched_env):
    collector = EnvCollector()
    snapshots = collector.collect()
    assert len(snapshots) == len(SAMPLE_ENV)


def test_snapshot_equality():
    s1 = ConfigSnapshot(source="env", key="APP_HOST", value="localhost")
    s2 = ConfigSnapshot(source="env", key="APP_HOST", value="localhost")
    s3 = ConfigSnapshot(source="env", key="APP_HOST", value="remotehost")
    assert s1 == s2
    assert s1 != s3


def test_snapshot_collected_at_is_datetime():
    s = ConfigSnapshot(source="env", key="X", value="y")
    assert isinstance(s.collected_at, datetime)


def test_validate_config_invalid_pattern():
    collector = EnvCollector(config={"pattern": "[invalid"})
    assert collector.validate_config() is False


def test_validate_config_valid_pattern():
    collector = EnvCollector(config={"pattern": r"^APP_.*"})
    assert collector.validate_config() is True


def test_collector_repr():
    collector = EnvCollector()
    assert "EnvCollector" in repr(collector)
    assert "env" in repr(collector)
