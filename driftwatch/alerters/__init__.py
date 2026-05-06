"""Alerter registry for driftwatch."""

from __future__ import annotations

from typing import Any, Dict

from driftwatch.alerters.file_alerter import FileAlerter
from driftwatch.alerters.log_alerter import LogAlerter
from driftwatch.alerters.webhook_alerter import WebhookAlerter

_ALERTER_REGISTRY: Dict[str, Any] = {
    "log": LogAlerter,
    "webhook": WebhookAlerter,
    "file": FileAlerter,
}


def get_alerter(alerter_type: str, **kwargs: Any):
    """Instantiate an alerter by type name.

    Parameters
    ----------
    alerter_type:
        One of ``log``, ``webhook``, or ``file``.
    **kwargs:
        Constructor arguments forwarded to the alerter class.

    Raises
    ------
    KeyError
        If *alerter_type* is not registered.
    """
    try:
        cls = _ALERTER_REGISTRY[alerter_type]
    except KeyError:
        available = ", ".join(sorted(_ALERTER_REGISTRY))
        raise KeyError(
            f"Unknown alerter type '{alerter_type}'. Available: {available}"
        ) from None
    return cls(**kwargs)


def list_alerters() -> list:
    """Return the names of all registered alerter types."""
    return sorted(_ALERTER_REGISTRY.keys())
