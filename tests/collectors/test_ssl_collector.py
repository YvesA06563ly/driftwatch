"""Tests for SslCollector."""
from __future__ import annotations

import ssl
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.ssl_collector import SslCollector

_NOT_BEFORE = datetime(2024, 1, 1, tzinfo=timezone.utc)
_NOT_AFTER = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _make_cert(not_after: datetime = _NOT_AFTER, not_before: datetime = _NOT_BEFORE):
    fmt = "%b %d %H:%M:%S %Y %Z"

    def _rdn(cn):
        return (("commonName", cn),)

    return {
        "subject": (_rdn("example.com"),),
        "issuer": (_rdn("Let's Encrypt"),),
        "notBefore": not_before.strftime(fmt).replace("+00:00", "GMT"),
        "notAfter": not_after.strftime(fmt).replace("+00:00", "GMT"),
        "serialNumber": "DEADBEEF",
    }


def _make_collector(hostnames=("example.com",), **kw):
    cfg = {"hostnames": list(hostnames), **kw}
    return SslCollector(cfg)


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_missing_hostnames_raises():
    with pytest.raises(ValueError, match="hostnames"):
        SslCollector({}).validate_config()


def test_validate_empty_hostnames_raises():
    with pytest.raises(ValueError, match="hostnames"):
        SslCollector({"hostnames": []}).validate_config()


def test_validate_bad_port_raises():
    with pytest.raises(ValueError, match="port"):
        SslCollector({"hostnames": ["example.com"], "port": 99999}).validate_config()


def test_validate_ok_does_not_raise():
    SslCollector({"hostnames": ["example.com"], "port": 443}).validate_config()


# ---------------------------------------------------------------------------
# collect — happy path
# ---------------------------------------------------------------------------

def _patch_ssl(cert, hostname="example.com", port=443):
    mock_ssock = MagicMock()
    mock_ssock.getpeercert.return_value = cert
    mock_ssock.__enter__ = lambda s: mock_ssock
    mock_ssock.__exit__ = MagicMock(return_value=False)

    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: mock_sock
    mock_sock.__exit__ = MagicMock(return_value=False)

    ctx_mock = MagicMock()
    ctx_mock.wrap_socket.return_value = mock_ssock

    return (
        patch("socket.create_connection", return_value=mock_sock),
        patch("ssl.create_default_context", return_value=ctx_mock),
    )


def test_collect_returns_snapshot_with_hostname_key():
    cert = _make_cert()
    p1, p2 = _patch_ssl(cert)
    with p1, p2:
        snap = _make_collector().collect()
    assert "example.com:443" in snap.data


def test_collect_ok_status_and_fields():
    cert = _make_cert()
    p1, p2 = _patch_ssl(cert)
    with p1, p2:
        snap = _make_collector().collect()
    entry = snap.data["example.com:443"]
    assert entry["status"] == "ok"
    assert entry["subject_cn"] == "example.com"
    assert entry["issuer_cn"] == "Let's Encrypt"
    assert entry["serial"] == "DEADBEEF"
    assert isinstance(entry["days_remaining"], int)


def test_collect_expired_cert_flags_expired():
    past = datetime.now(tz=timezone.utc) - timedelta(days=10)
    cert = _make_cert(not_after=past)
    p1, p2 = _patch_ssl(cert)
    with p1, p2:
        snap = _make_collector().collect()
    assert snap.data["example.com:443"]["expired"] is True


def test_collect_connection_error_records_error_status():
    collector = _make_collector()
    with patch("socket.create_connection", side_effect=OSError("refused")):
        snap = collector.collect()
    entry = snap.data["example.com:443"]
    assert entry["status"] == "error"
    assert "refused" in entry["error"]


def test_collect_multiple_hostnames():
    cert = _make_cert()
    p1, p2 = _patch_ssl(cert)
    with p1, p2:
        snap = _make_collector(hostnames=["example.com", "other.com"]).collect()
    assert "example.com:443" in snap.data
    assert "other.com:443" in snap.data


def test_collect_custom_port():
    cert = _make_cert()
    p1, p2 = _patch_ssl(cert)
    with p1, p2:
        snap = _make_collector(port=8443).collect()
    assert "example.com:8443" in snap.data


def test_collect_snapshot_source_is_ssl():
    cert = _make_cert()
    p1, p2 = _patch_ssl(cert)
    with p1, p2:
        snap = _make_collector().collect()
    assert snap.source == "ssl"
