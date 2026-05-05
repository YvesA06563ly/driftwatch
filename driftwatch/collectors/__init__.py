"""Collector registry for driftwatch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseCollector, ConfigSnapshot
from .env_collector import EnvCollector
from .file_collector import FileCollector
from .process_collector import ProcessCollector

if TYPE_CHECKING:
    from typing import Any

_REGISTRY: dict[str, type[BaseCollector]] = {
    "env": EnvCollector,
    "file": FileCollector,
    "process": ProcessCollector,
}


def get_collector(kind: str, config: dict[str, Any]) -> BaseCollector:
    """Instantiate and validate a collector by *kind* name.

    Parameters
    ----------
    kind:
        One of the registered collector type names (``"env"``, ``"file"``,
        ``"process"``).
    config:
        Collector-specific configuration dictionary.

    Raises
    ------
    KeyError
        If *kind* is not registered.
    ValueError
        If the collector's ``validate_config`` check fails.
    """
    try:
        cls = _REGISTRY[kind]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(
            f"Unknown collector kind {kind!r}. Available: {available}"
        ) from None

    collector = cls(config)
    collector.validate_config()
    return collector


__all__ = [
    "BaseCollector",
    "ConfigSnapshot",
    "EnvCollector",
    "FileCollector",
    "ProcessCollector",
    "get_collector",
]
