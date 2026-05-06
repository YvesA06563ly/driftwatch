"""Tests for SystemdCollector."""
from __future__ import annotations

import pytest

from driftwatch.collectors.systemd_collector import SystemdCollector


SHOW_OUTPUT = "ActiveState=active\nSubState=running\nLoadState=loaded\nUnitFileState=enabled\n"


def _make_collector(config):
    c = SystemdCollector(config)
    c.validate_config()
    return c


def test_validate_requires_units_or_pattern():
    with pytest.raises(ValueError, match="units.*pattern"):
        SystemdCollector({}).validate_config()


def test_validate_bad_pattern_raises():
    with pytest.raises(ValueError, match="Invalid pattern"):
        SystemdCollector({"pattern": "[invalid"}).validate_config()


def test_collect_explicit_units(mocker):
    mocker.patch(
        "driftwatch.collectors.systemd_collector.subprocess.run",
        return_value=mocker.Mock(stdout=SHOW_OUTPUT, returncode=0),
    )
    c = _make_collector({"units": ["sshd.service", "nginx.service"]})
    snap = c.collect()
    assert snap.source == "systemd"
    assert "sshd.service" in snap.data
    assert snap.data["sshd.service"]["ActiveState"] == "active"


def test_collect_with_pattern(mocker):
    list_output = "sshd.service active\nnginx.service inactive\ncron.service active\n"
    run = mocker.patch("driftwatch.collectors.systemd_collector.subprocess.run")
    run.side_effect = [
        mocker.Mock(stdout=list_output, returncode=0),
        mocker.Mock(stdout=SHOW_OUTPUT, returncode=0),
    ]
    c = _make_collector({"pattern": "^sshd"})
    snap = c.collect()
    assert "sshd.service" in snap.data


def test_collect_excludes_inactive_by_default(mocker):
    inactive_output = "ActiveState=inactive\nSubState=dead\nLoadState=loaded\nUnitFileState=disabled\n"
    mocker.patch(
        "driftwatch.collectors.systemd_collector.subprocess.run",
        return_value=mocker.Mock(stdout=inactive_output, returncode=0),
    )
    c = _make_collector({"units": ["stopped.service"]})
    snap = c.collect()
    assert "stopped.service" not in snap.data


def test_collect_includes_inactive_when_configured(mocker):
    inactive_output = "ActiveState=inactive\nSubState=dead\nLoadState=loaded\nUnitFileState=disabled\n"
    mocker.patch(
        "driftwatch.collectors.systemd_collector.subprocess.run",
        return_value=mocker.Mock(stdout=inactive_output, returncode=0),
    )
    c = _make_collector({"units": ["stopped.service"], "include_inactive": True})
    snap = c.collect()
    assert "stopped.service" in snap.data
    assert snap.data["stopped.service"]["ActiveState"] == "inactive"


def test_collect_deduplicates_units(mocker):
    run = mocker.patch("driftwatch.collectors.systemd_collector.subprocess.run")
    list_out = "sshd.service active\n"
    run.side_effect = [
        mocker.Mock(stdout=list_out, returncode=0),
        mocker.Mock(stdout=SHOW_OUTPUT, returncode=0),
    ]
    c = _make_collector({"units": ["sshd.service"], "pattern": "^sshd"})
    snap = c.collect()
    assert list(snap.data.keys()).count("sshd.service") == 1
