"""Tests for GrafanaAnnotationAlerter."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.alerters.grafana_annotation_alerter import GrafanaAnnotationAlerter
from driftwatch.detectors.drift_detector import DriftEvent


BASE_CONFIG = {
    "url": "https://grafana.example.com",
    "api_key": "glsa_secret",
    "dashboard_id": 42,
    "panel_id": 7,
    "tags": ["driftwatch", "ci"],
}


def _make_event(key="cfg/timeout", change_type="modified", old=30, new=60):
    return DriftEvent(key=key, change_type=change_type, old_value=old, new_value=new, source="test")


def _mock_response(status=200):
    r = MagicMock()
    r.status_code = status
    r.raise_for_status = MagicMock()
    return r


@pytest.fixture()
def alerter():
    return GrafanaAnnotationAlerter(BASE_CONFIG)


def test_empty_url_raises():
    with pytest.raises(ValueError, match="url"):
        GrafanaAnnotationAlerter({**BASE_CONFIG, "url": ""})


def test_non_http_url_raises():
    with pytest.raises(ValueError, match="http"):
        GrafanaAnnotationAlerter({**BASE_CONFIG, "url": "grpc://bad"})


def test_empty_api_key_raises():
    with pytest.raises(ValueError, match="api_key"):
        GrafanaAnnotationAlerter({**BASE_CONFIG, "api_key": ""})


def test_emit_no_events_posts_nothing(alerter):
    with patch("driftwatch.alerters.grafana_annotation_alerter.requests.post") as mock_post:
        alerter.emit([])
        mock_post.assert_not_called()


def test_emit_single_event_posts_once(alerter):
    with patch("driftwatch.alerters.grafana_annotation_alerter.requests.post") as mock_post:
        mock_post.return_value = _mock_response()
        alerter.emit([_make_event()])
        assert mock_post.call_count == 1


def test_emit_payload_contains_key_and_change_type(alerter):
    with patch("driftwatch.alerters.grafana_annotation_alerter.requests.post") as mock_post:
        mock_post.return_value = _mock_response()
        alerter.emit([_make_event(key="cfg/timeout", change_type="modified")])
        _, kwargs = mock_post.call_args
        text = kwargs["json"]["text"]
        assert "cfg/timeout" in text
        assert "modified" in text


def test_emit_payload_includes_dashboard_and_panel(alerter):
    with patch("driftwatch.alerters.grafana_annotation_alerter.requests.post") as mock_post:
        mock_post.return_value = _mock_response()
        alerter.emit([_make_event()])
        payload = mock_post.call_args[1]["json"]
        assert payload["dashboardId"] == 42
        assert payload["panelId"] == 7


def test_emit_uses_bearer_auth(alerter):
    with patch("driftwatch.alerters.grafana_annotation_alerter.requests.post") as mock_post:
        mock_post.return_value = _mock_response()
        alerter.emit([_make_event()])
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer glsa_secret"


def test_emit_summary_posts_once_for_multiple_events(alerter):
    with patch("driftwatch.alerters.grafana_annotation_alerter.requests.post") as mock_post:
        mock_post.return_value = _mock_response()
        alerter.emit_summary([_make_event(), _make_event(key="other")])
        assert mock_post.call_count == 1
        payload = mock_post.call_args[1]["json"]
        assert "2" in payload["text"]


def test_emit_summary_no_events_posts_nothing(alerter):
    with patch("driftwatch.alerters.grafana_annotation_alerter.requests.post") as mock_post:
        alerter.emit_summary([])
        mock_post.assert_not_called()
