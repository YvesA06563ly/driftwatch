"""Tests for WebhookAlerter."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.alerters.webhook_alerter import WebhookAlerter
from driftwatch.detectors.drift_detector import DriftEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def alerter() -> WebhookAlerter:
    return WebhookAlerter("https://hooks.example.com/drift", timeout=5)


def _make_event(key: str = "DB_HOST", kind: str = "changed") -> DriftEvent:
    return DriftEvent(
        collector="env",
        key=key,
        kind=kind,
        old_value="old" if kind != "added" else None,
        new_value="new" if kind != "removed" else None,
    )


def _mock_response(status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="url"):
        WebhookAlerter("")


def test_default_content_type_header() -> None:
    a = WebhookAlerter("https://example.com")
    assert a.headers["Content-Type"] == "application/json"


def test_extra_headers_merged() -> None:
    a = WebhookAlerter("https://example.com", headers={"Authorization": "Bearer tok"})
    assert "Authorization" in a.headers
    assert a.headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# emit — individual events
# ---------------------------------------------------------------------------


def test_emit_posts_each_event(alerter: WebhookAlerter) -> None:
    events = [_make_event("A"), _make_event("B")]
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        alerter.emit(events)
    assert mock_open.call_count == 2


def test_emit_payload_is_valid_json(alerter: WebhookAlerter) -> None:
    captured: list[bytes] = []

    def fake_open(req, timeout):  # noqa: ANN001
        captured.append(req.data)
        return _mock_response(200)

    with patch("urllib.request.urlopen", side_effect=fake_open):
        alerter.emit([_make_event()])

    payload = json.loads(captured[0])
    assert payload["key"] == "DB_HOST"
    assert payload["kind"] == "changed"


def test_emit_empty_list_does_nothing(alerter: WebhookAlerter) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        alerter.emit([])
    mock_open.assert_not_called()


def test_emit_http_error_does_not_raise(alerter: WebhookAlerter) -> None:
    err = urllib.error.HTTPError(alerter.url, 500, "Server Error", {}, None)
    with patch("urllib.request.urlopen", side_effect=err):
        alerter.emit([_make_event()])  # should not raise


# ---------------------------------------------------------------------------
# emit_summary — batched payload
# ---------------------------------------------------------------------------


def test_emit_summary_sends_single_request(alerter: WebhookAlerter) -> None:
    events = [_make_event("X"), _make_event("Y", "added")]
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        alerter.emit_summary(events)
    assert mock_open.call_count == 1


def test_emit_summary_payload_structure(alerter: WebhookAlerter) -> None:
    captured: list[bytes] = []

    def fake_open(req, timeout):  # noqa: ANN001
        captured.append(req.data)
        return _mock_response(200)

    events = [_make_event("K1"), _make_event("K2", "removed")]
    with patch("urllib.request.urlopen", side_effect=fake_open):
        alerter.emit_summary(events)

    payload = json.loads(captured[0])
    assert payload["event_type"] == "drift_summary"
    assert payload["total"] == 2
    assert len(payload["events"]) == 2


def test_emit_summary_skipped_when_disabled() -> None:
    a = WebhookAlerter("https://example.com", include_summary=False)
    with patch("urllib.request.urlopen") as mock_open:
        a.emit_summary([_make_event()])
    mock_open.assert_not_called()


def test_emit_summary_empty_events_skipped(alerter: WebhookAlerter) -> None:
    with patch("urllib.request.urlopen") as mock_open:
        alerter.emit_summary([])
    mock_open.assert_not_called()
