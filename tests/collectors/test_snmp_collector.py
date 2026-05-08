"""Tests for SnmpCollector."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.snmp_collector import SnmpCollector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_collector(**kwargs) -> SnmpCollector:
    cfg = {"targets": ["192.0.2.1"], "oids": ["1.3.6.1.2.1.1.1.0"], **kwargs}
    return SnmpCollector(cfg)


def _stub_pysnmp(var_binds=None, error_indication=None, error_status=None):
    """Inject a fake pysnmp.hlapi into sys.modules."""
    oid_val = MagicMock()
    oid_val.prettyPrint.return_value = "Linux router 5.4.0"

    if var_binds is None:
        var_binds = [(MagicMock(), oid_val)]

    fake_get_cmd = MagicMock(
        return_value=iter([(error_indication, error_status, None, var_binds)])
    )

    hlapi = ModuleType("pysnmp.hlapi")
    for name in (
        "SnmpEngine", "CommunityData", "ContextData",
        "ObjectIdentity", "ObjectType", "UdpTransportTarget",
    ):
        setattr(hlapi, name, MagicMock())
    hlapi.getCmd = fake_get_cmd

    pysnmp_mod = ModuleType("pysnmp")
    sys.modules.setdefault("pysnmp", pysnmp_mod)
    sys.modules["pysnmp.hlapi"] = hlapi
    return hlapi


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_config_ok():
    _make_collector()  # should not raise


def test_validate_config_empty_targets_raises():
    with pytest.raises(ValueError, match="targets"):
        SnmpCollector({"targets": [], "oids": ["1.3.6.1.2.1.1.1.0"]})


def test_validate_config_empty_oids_raises():
    with pytest.raises(ValueError, match="oids"):
        SnmpCollector({"targets": ["192.0.2.1"], "oids": []})


def test_validate_config_bad_timeout_raises():
    with pytest.raises(ValueError, match="timeout"):
        _make_collector(timeout=0)


def test_validate_config_default_community_and_port():
    c = _make_collector()
    assert c._community == "public"
    assert c._timeout == 5


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def test_collect_returns_snapshot_with_oid_value():
    hlapi = _stub_pysnmp()
    c = _make_collector()
    snap = c.collect()
    assert snap.source == "snmp"
    key = "192.0.2.1:161/1.3.6.1.2.1.1.1.0"
    assert key in snap.data
    assert snap.data[key] == "Linux router 5.4.0"


def test_collect_error_indication_stored_as_error():
    _stub_pysnmp(error_indication="No SNMP response received", var_binds=[])
    c = _make_collector()
    snap = c.collect()
    key = "192.0.2.1:161/1.3.6.1.2.1.1.1.0"
    assert snap.data[key].startswith("__error__:")


def test_collect_custom_port_in_key():
    hlapi = _stub_pysnmp()
    c = _make_collector(targets=["10.0.0.1:1161"])
    snap = c.collect()
    key = "10.0.0.1:1161/1.3.6.1.2.1.1.1.0"
    assert key in snap.data


def test_collect_multiple_oids():
    hlapi = _stub_pysnmp()
    c = _make_collector(
        oids=["1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1.3.0"]
    )
    snap = c.collect()
    assert len(snap.data) == 2
