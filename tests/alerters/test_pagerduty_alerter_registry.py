"""Verify PagerDutyAlerter is accessible through the alerter registry."""
from __future__ import annotations

import pytest

from driftwatch.alerters import get_alerter, list_alerters
from driftwatch.alerters.pagerduty_alerter import PagerDutyAlerter


def test_pagerduty_in_list_alerters() -> None:
    assert "pagerduty" in list_alerters()


def test_get_alerter_returns_pagerduty_instance() -> None:
    alerter = get_alerter("pagerduty", {"routing_key": "test-key"})
    assert isinstance(alerter, PagerDutyAlerter)


def test_get_alerter_pagerduty_invalid_config_raises() -> None:
    with pytest.raises(ValueError, match="routing_key"):
        get_alerter("pagerduty", {})


def test_get_alerter_pagerduty_custom_severity() -> None:
    alerter = get_alerter(
        "pagerduty", {"routing_key": "k", "severity": "error"}
    )
    assert isinstance(alerter, PagerDutyAlerter)
    assert alerter._severity == "error"
