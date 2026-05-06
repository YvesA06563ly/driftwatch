"""Tests for PagerDutyAlerter."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.alerters.pagerduty_alerter import PagerDutyAlerter, _EVENTS_URL
from driftwatch.detectors.drift_detector import DriftEvent


@pytest.fixture()
def alerter() -> PagerDutyAlerter:
    return PagerDutyAlerter({"routing_key": "abc123", "severity": "critical"})


def _make_event(
    key: str = "PORT",
    change_type: str = "changed",
    old: str | None = "80",
    new: str | None = "8080",
    collector: str = "env",
) -> DriftEvent:
    return DriftEvent(
        collector=collector,
        key=key,
        change_type=change_type,
        old_value=old,
        new_value=new,
    )


def _mock_response(status: int = 202) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_empty_routing_key_raises() -> None:
    with pytest.raises(ValueError, match="routing_key"):
        PagerDutyAlerter({"routing_key": ""})


def test_missing_routing_key_raises() -> None:
    with pytest.raises(ValueError, match="routing_key"):
        PagerDutyAlerter({})


def test_build_payload_structure(alerter: PagerDutyAlerter) -> None:
    event = _make_event()
    payload = alerter._build_payload(event)
    assert payload["routing_key"] == "abc123"
    assert payload["event_action"] == "trigger"
    assert "summary" in payload["payload"]
    assert payload["payload"]["severity"] == "critical"
    assert payload["payload"]["custom_details"]["key"] == "PORT"


def test_emit_posts_one_request_per_event(alerter: PagerDutyAlerter) -> None:
    events = [_make_event("A"), _make_event("B")]
    with patch("urllib.request.urlopen", return_value=_mock_response()) as mock_open:
        alerter.emit(events)
    assert mock_open.call_count == 2


def test_emit_no_events_makes_no_requests(alerter: PagerDutyAlerter) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        alerter.emit([])
    mock_open.assert_not_called()


def test_emit_sends_correct_url(alerter: PagerDutyAlerter) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response()) as mock_open:
        alerter.emit([_make_event()])
    req = mock_open.call_args[0][0]
    assert req.full_url == _EVENTS_URL


def test_emit_sends_json_body(alerter: PagerDutyAlerter) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response()) as mock_open:
        alerter.emit([_make_event(key="DB_HOST")])
    req = mock_open.call_args[0][0]
    body = json.loads(req.data)
    assert body["payload"]["custom_details"]["key"] == "DB_HOST"


def test_emit_raises_on_bad_status(alerter: PagerDutyAlerter) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(500)):
        with pytest.raises(RuntimeError, match="500"):
            alerter.emit([_make_event()])


def test_emit_summary_delegates_to_emit(alerter: PagerDutyAlerter) -> None:
    events = [_make_event()]
    with patch.object(alerter, "emit") as mock_emit:
        alerter.emit_summary(events)
    mock_emit.assert_called_once_with(events)


def test_default_severity_is_warning() -> None:
    a = PagerDutyAlerter({"routing_key": "key"})
    payload = a._build_payload(_make_event())
    assert payload["payload"]["severity"] == "warning"


def test_custom_source() -> None:
    a = PagerDutyAlerter({"routing_key": "key", "source": "myapp"})
    payload = a._build_payload(_make_event())
    assert payload["payload"]["source"] == "myapp"
