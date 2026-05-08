"""Tests for DnsCollector."""
from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from driftwatch.collectors.dns_collector import DnsCollector


def _make_collector(extra: dict | None = None) -> DnsCollector:
    cfg = {"hostnames": ["example.com"], **(extra or {})}
    return DnsCollector(cfg)


def _addrinfo(ip: str, family=socket.AF_INET):
    return [(family, socket.SOCK_STREAM, 0, "", (ip, 0))]


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_empty_hostnames_raises():
    with pytest.raises(ValueError, match="hostname"):
        DnsCollector({"hostnames": []}).validate_config()


def test_validate_missing_hostnames_raises():
    with pytest.raises(ValueError, match="hostname"):
        DnsCollector({}).validate_config()


def test_validate_bad_record_type_raises():
    with pytest.raises(ValueError, match="unsupported record_types"):
        DnsCollector({"hostnames": ["example.com"], "record_types": ["TXT"]}).validate_config()


def test_validate_invalid_hostname_raises():
    with pytest.raises(ValueError, match="invalid hostname"):
        DnsCollector({"hostnames": ["bad hostname!"]}).validate_config()


def test_validate_ok_does_not_raise():
    _make_collector({"record_types": ["A", "AAAA"]}).validate_config()


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

def test_collect_returns_snapshot_with_hostname_key():
    c = _make_collector()
    with patch("socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        snap = c.collect()
    assert "example.com" in snap.data


def test_collect_a_record_sorted():
    c = _make_collector()
    ips = ["10.0.0.2", "10.0.0.1"]
    with patch("socket.getaddrinfo", return_value=_addrinfo("10.0.0.2") + _addrinfo("10.0.0.1")):
        snap = c.collect()
    assert snap.data["example.com"]["A"] == sorted(ips)


def test_collect_dns_error_returns_error_string():
    c = _make_collector()
    with patch("socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN")):
        snap = c.collect()
    assert snap.data["example.com"]["A"][0].startswith("ERROR:")


def test_collect_multiple_hostnames():
    c = DnsCollector({"hostnames": ["a.example.com", "b.example.com"]})
    with patch("socket.getaddrinfo", return_value=_addrinfo("1.2.3.4")):
        snap = c.collect()
    assert set(snap.data.keys()) == {"a.example.com", "b.example.com"}


def test_collect_snapshot_source_is_dns():
    c = _make_collector()
    with patch("socket.getaddrinfo", return_value=_addrinfo("1.1.1.1")):
        snap = c.collect()
    assert snap.source == "dns"


def test_collect_aaaa_uses_af_inet6():
    c = DnsCollector({"hostnames": ["example.com"], "record_types": ["AAAA"]})
    called_families = []

    def fake_gai(host, port, family):
        called_families.append(family)
        return _addrinfo("::1", family=socket.AF_INET6)

    with patch("socket.getaddrinfo", side_effect=fake_gai):
        c.collect()
    assert socket.AF_INET6 in called_families
