"""Alerter registry — maps string type names to alerter classes."""
from __future__ import annotations

from typing import Any

from driftwatch.alerters.file_alerter import FileAlerter
from driftwatch.alerters.log_alerter import LogAlerter
from driftwatch.alerters.pagerduty_alerter import PagerDutyAlerter
from driftwatch.alerters.slack_alerter import SlackAlerter
from driftwatch.alerters.webhook_alerter import WebhookAlerter

_REGISTRY: dict[str, type] = {
    "log": LogAlerter,
    "file": FileAlerter,
    "webhook": WebhookAlerter,
    "slack": SlackAlerter,
    "pagerduty": PagerDutyAlerter,
}


def list_alerters() -> list[str]:
    """Return sorted list of registered alerter type names."""
    return sorted(_REGISTRY.keys())


def get_alerter(alerter_type: str, config: dict[str, Any]) -> Any:
    """Instantiate and return an alerter by type name.

    Raises:
        KeyError: if *alerter_type* is not registered.
        ValueError: if the alerter rejects *config*.
    """
    if alerter_type not in _REGISTRY:
        raise KeyError(
            f"Unknown alerter type '{alerter_type}'. "
            f"Available: {list_alerters()}"
        )
    return _REGISTRY[alerter_type](config)
