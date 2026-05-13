"""Tests for SyslogCollector."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.syslog_collector import SyslogCollector


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_collector(**kwargs) -> SyslogCollector:
    cfg = {"units": ["nginx.service"], **kwargs}
    return SyslogCollector(cfg)


SAMPLE_JOURNAL = "2024-01-15T10:00:00+0000 host nginx[123]: started\n" \
                 "2024-01-15T10:01:00+0000 host nginx[123]: request\n"


def _fake_run(cmd, **kwargs):
    proc = MagicMock()
    if "journalctl" in cmd:
        proc.stdout = SAMPLE_JOURNAL
    elif "systemctl" in cmd:
        proc.stdout = "nginx.service  loaded active running\n" \
                      "sshd.service   loaded active running\n"
    else:
        proc.stdout = ""
    return proc


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_requires_units_or_pattern():
    with pytest.raises(ValueError, match="units.*pattern"):
        SyslogCollector({}).validate_config()


def test_validate_bad_pattern_raises():
    with pytest.raises(ValueError, match="Invalid 'pattern'"):
        SyslogCollector({"pattern": "[unclosed"}).validate_config()


def test_validate_ok_with_units():
    _make_collector().validate_config()  # should not raise


def test_validate_ok_with_pattern():
    SyslogCollector({"pattern": "nginx"}).validate_config()  # should not raise


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def test_collect_explicit_units():
    c = _make_collector()
    with patch("subprocess.run", side_effect=_fake_run):
        snap = c.collect()

    assert snap.collector == "syslog"
    assert "nginx.service" in snap.data
    assert snap.data["nginx.service"]["count"] == 2


def test_collect_latest_timestamp_captured():
    c = _make_collector()
    with patch("subprocess.run", side_effect=_fake_run):
        snap = c.collect()

    assert snap.data["nginx.service"]["latest"] is not None


def test_collect_with_pattern_discovers_units():
    c = SyslogCollector({"pattern": r"nginx\.service"})
    with patch("subprocess.run", side_effect=_fake_run):
        snap = c.collect()

    assert "nginx.service" in snap.data


def test_collect_journalctl_not_found_returns_zero_count():
    c = _make_collector()

    def _raise(cmd, **kw):
        if "journalctl" in cmd:
            raise FileNotFoundError
        return MagicMock(stdout="")

    with patch("subprocess.run", side_effect=_raise):
        snap = c.collect()

    assert snap.data["nginx.service"]["count"] == 0
    assert snap.data["nginx.service"]["latest"] is None


def test_collect_timeout_returns_zero_count():
    c = _make_collector()

    def _timeout(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 10)

    with patch("subprocess.run", side_effect=_timeout):
        snap = c.collect()

    assert snap.data["nginx.service"]["count"] == 0


def test_collect_snapshot_has_collected_at():
    c = _make_collector()
    with patch("subprocess.run", side_effect=_fake_run):
        snap = c.collect()
    assert snap.collected_at is not None
