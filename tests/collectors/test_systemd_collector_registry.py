"""Registry integration tests for SystemdCollector."""
from __future__ import annotations

import pytest

from driftwatch.collectors import get_collector, list_collectors


def test_systemd_in_list_collectors():
    assert "systemd" in list_collectors()


def test_get_collector_returns_systemd_instance():
    from driftwatch.collectors.systemd_collector import SystemdCollector

    c = get_collector("systemd", {"units": ["sshd.service"]})
    assert isinstance(c, SystemdCollector)


def test_get_collector_systemd_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("systemd", {})


def test_get_collector_systemd_collect_via_registry(mocker):
    show_out = "ActiveState=active\nSubState=running\nLoadState=loaded\nUnitFileState=enabled\n"
    mocker.patch(
        "driftwatch.collectors.systemd_collector.subprocess.run",
        return_value=mocker.Mock(stdout=show_out, returncode=0),
    )
    c = get_collector("systemd", {"units": ["sshd.service"]})
    snap = c.collect()
    assert snap.source == "systemd"
    assert "sshd.service" in snap.data
