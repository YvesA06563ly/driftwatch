"""Integration tests: DnsCollector through the collector registry."""
from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from driftwatch.collectors import get_collector, list_collectors


def _addrinfo(ip: str):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]


def test_dns_in_list_collectors():
    assert "dns" in list_collectors()


def test_get_collector_returns_dns_instance():
    from driftwatch.collectors.dns_collector import DnsCollector
    c = get_collector("dns", {"hostnames": ["example.com"]})
    assert isinstance(c, DnsCollector)


def test_get_collector_dns_invalid_config_raises():
    with pytest.raises(ValueError):
        get_collector("dns", {"hostnames": []})


def test_get_collector_dns_collect_via_registry():
    c = get_collector("dns", {"hostnames": ["example.com"]})
    with patch("socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        snap = c.collect()
    assert "example.com" in snap.data
    assert snap.data["example.com"]["A"] == ["93.184.216.34"]
