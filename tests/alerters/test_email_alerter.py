"""Tests for EmailAlerter."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.alerters.email_alerter import EmailAlerter
from driftwatch.detectors.drift_detector import DriftEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def base_config() -> dict:
    return {
        "smtp_host": "smtp.example.com",
        "port": 587,
        "from": "drift@example.com",
        "to": ["ops@example.com"],
        "username": "user",
        "password": "secret",
        "use_tls": True,
    }


@pytest.fixture()
def alerter(base_config) -> EmailAlerter:
    return EmailAlerter(base_config)


def _make_event(key: str = "ENV/FOO", change_type: str = "changed") -> DriftEvent:
    return DriftEvent(
        collector="env",
        key=key,
        change_type=change_type,
        baseline_value="old",
        current_value="new",
    )


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

def test_empty_smtp_host_raises(base_config):
    base_config["smtp_host"] = ""
    with pytest.raises(ValueError, match="smtp_host"):
        EmailAlerter(base_config)


def test_missing_to_raises(base_config):
    base_config["to"] = []
    with pytest.raises(ValueError, match="to"):
        EmailAlerter(base_config)


def test_missing_from_raises(base_config):
    base_config["from"] = ""
    with pytest.raises(ValueError, match="from"):
        EmailAlerter(base_config)


# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------

def test_emit_no_events_sends_nothing(alerter):
    with patch("driftwatch.alerters.email_alerter.smtplib.SMTP") as mock_smtp:
        alerter.emit([])
        mock_smtp.assert_not_called()


def test_emit_single_event_sends_email(alerter):
    event = _make_event()
    with patch.object(alerter, "_send") as mock_send:
        alerter.emit([event])
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "changed" in subject
        assert "ENV/FOO" in subject
        payload = json.loads(body)
        assert payload["key"] == "ENV/FOO"


def test_emit_multiple_events_sends_one_email_each(alerter):
    events = [_make_event(f"KEY/{i}") for i in range(3)]
    with patch.object(alerter, "_send") as mock_send:
        alerter.emit(events)
        assert mock_send.call_count == 3


# ---------------------------------------------------------------------------
# emit_summary
# ---------------------------------------------------------------------------

def test_emit_summary_no_events_sends_nothing(alerter):
    with patch.object(alerter, "_send") as mock_send:
        alerter.emit_summary([])
        mock_send.assert_not_called()


def test_emit_summary_sends_single_email(alerter):
    events = [_make_event(f"KEY/{i}") for i in range(4)]
    with patch.object(alerter, "_send") as mock_send:
        alerter.emit_summary(events)
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "4" in subject
        assert "drift event" in subject.lower()
        assert "KEY/0" in body


def test_subject_prefix_applied(base_config):
    base_config["subject_prefix"] = "[PROD]"
    a = EmailAlerter(base_config)
    with patch.object(a, "_send") as mock_send:
        a.emit([_make_event()])
        subject = mock_send.call_args[0][0]
        assert subject.startswith("[PROD]")
