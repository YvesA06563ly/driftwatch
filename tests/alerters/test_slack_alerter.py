"""Tests for SlackAlerter."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.alerters.slack_alerter import SlackAlerter
from driftwatch.detectors.drift_detector import DriftEvent

VALID_URL = "https://hooks.slack.com/services/T000/B000/xxxx"


@pytest.fixture()
def alerter() -> SlackAlerter:
    return SlackAlerter({"webhook_url": VALID_URL})


def _make_event(key: str = "FOO", change_type: str = "changed") -> DriftEvent:
    return DriftEvent(
        collector="env",
        key=key,
        change_type=change_type,
        old_value="old",
        new_value="new",
    )


def _mock_response(status: int = 200) -> Any:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SlackAlerter({"webhook_url": ""})


def test_non_https_url_raises() -> None:
    with pytest.raises(ValueError, match="https"):
        SlackAlerter({"webhook_url": "http://hooks.slack.com/bad"})


def test_default_username(alerter: SlackAlerter) -> None:
    assert alerter._username == "DriftWatch"


def test_custom_username() -> None:
    a = SlackAlerter({"webhook_url": VALID_URL, "username": "Bot"})
    assert a._username == "Bot"


def test_emit_no_events_does_not_post(alerter: SlackAlerter) -> None:
    with patch("driftwatch.alerters.slack_alerter.urllib.request.urlopen") as mock_open:
        alerter.emit([])
        mock_open.assert_not_called()


def test_emit_single_event_posts_json(alerter: SlackAlerter) -> None:
    event = _make_event("DB_HOST", "changed")
    with patch("driftwatch.alerters.slack_alerter.urllib.request.urlopen") as mock_open:
        mock_open.return_value = _mock_response(200)
        alerter.emit([event])
        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert "DB_HOST" in payload["text"]
        assert "changed" in payload["text"]
        assert payload["username"] == "DriftWatch"


def test_emit_summary_posts_even_when_empty(alerter: SlackAlerter) -> None:
    with patch("driftwatch.alerters.slack_alerter.urllib.request.urlopen") as mock_open:
        mock_open.return_value = _mock_response(200)
        alerter.emit_summary([])
        mock_open.assert_called_once()
        req = mock_open.call_args[0][0]
        payload = json.loads(req.data.decode())
        assert "0 event(s)" in payload["text"]


def test_http_error_is_logged(alerter: SlackAlerter, caplog: Any) -> None:
    import urllib.error

    with patch("driftwatch.alerters.slack_alerter.urllib.request.urlopen") as mock_open:
        mock_open.side_effect = urllib.error.HTTPError(
            VALID_URL, 500, "Internal Server Error", {}, None  # type: ignore[arg-type]
        )
        with caplog.at_level("ERROR", logger="driftwatch.alerters.slack_alerter"):
            alerter.emit([_make_event()])
        assert "HTTP error" in caplog.text


def test_url_error_is_logged(alerter: SlackAlerter, caplog: Any) -> None:
    import urllib.error

    with patch("driftwatch.alerters.slack_alerter.urllib.request.urlopen") as mock_open:
        mock_open.side_effect = urllib.error.URLError("connection refused")
        with caplog.at_level("ERROR", logger="driftwatch.alerters.slack_alerter"):
            alerter.emit([_make_event()])
        assert "URL error" in caplog.text
