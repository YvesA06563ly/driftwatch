"""Tests for ProcessCollector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.process_collector import ProcessCollector


def _make_proc(pid: int, name: str, status: str = "running", cmdline: list[str] | None = None) -> MagicMock:
    proc = MagicMock()
    proc.info = {
        "pid": pid,
        "name": name,
        "status": status,
        "cmdline": cmdline or [],
    }
    return proc


FAKE_PROCS = [
    _make_proc(1, "systemd", cmdline=["/sbin/init"]),
    _make_proc(100, "nginx", cmdline=["nginx", "-g", "daemon off;"]),
    _make_proc(200, "python3", cmdline=["python3", "app.py"]),
    _make_proc(300, "sshd"),
]


@pytest.fixture()
def patched_procs():
    with patch(
        "driftwatch.collectors.process_collector.psutil.process_iter",
        return_value=iter(FAKE_PROCS),
    ) as mock:
        yield mock


def test_collect_no_filter_returns_all(patched_procs):
    collector = ProcessCollector({})
    snapshot = collector.collect()
    assert snapshot.source == "process"
    assert set(snapshot.data.keys()) == {"1", "100", "200", "300"}


def test_collect_with_name_pattern(patched_procs):
    collector = ProcessCollector({"name_pattern": "nginx|sshd"})
    snapshot = collector.collect()
    assert set(snapshot.data.keys()) == {"100", "300"}


def test_collect_with_pid_filter(patched_procs):
    collector = ProcessCollector({"pids": [1, 200]})
    snapshot = collector.collect()
    assert set(snapshot.data.keys()) == {"1", "200"}


def test_collect_includes_cmdline(patched_procs):
    collector = ProcessCollector({"name_pattern": "nginx", "include_cmdline": True})
    snapshot = collector.collect()
    assert snapshot.data["100"]["cmdline"] == ["nginx", "-g", "daemon off;"]


def test_collect_excludes_cmdline_by_default(patched_procs):
    collector = ProcessCollector({"name_pattern": "nginx"})
    snapshot = collector.collect()
    assert "cmdline" not in snapshot.data["100"]


def test_validate_config_invalid_regex():
    collector = ProcessCollector({"name_pattern": "[invalid"})
    with pytest.raises(ValueError, match="Invalid name_pattern regex"):
        collector.validate_config()


def test_validate_config_invalid_pids_type():
    collector = ProcessCollector({"pids": "not-a-list"})
    with pytest.raises(ValueError, match="'pids' must be a list"):
        collector.validate_config()


def test_snapshot_equality(patched_procs):
    c1 = ProcessCollector({})
    c2 = ProcessCollector({})
    assert c1.collect() == c2.collect()
