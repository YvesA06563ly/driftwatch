"""Configuration loading and validation for driftwatch."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from driftwatch.collectors import list_collectors
from driftwatch.alerters import list_alerters


class ConfigError(ValueError):
    """Raised when the driftwatch configuration is invalid."""


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load a TOML configuration file and return the parsed dict."""
    data = Path(path).read_bytes()
    try:
        cfg = tomllib.loads(data.decode())
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"failed to parse config: {exc}") from exc
    validate_config(cfg)
    return cfg


def validate_config(cfg: Any) -> None:  # noqa: C901
    """Validate the top-level configuration structure.

    Raises
    ------
    ConfigError
        On any structural or reference error.
    """
    if not isinstance(cfg, dict):
        raise ConfigError("configuration must be a TOML table (dict)")

    if "collectors" not in cfg:
        raise ConfigError("configuration must contain a 'collectors' section")

    known_collectors = set(list_collectors())
    known_alerters = set(list_alerters())

    collectors = cfg["collectors"]
    if not isinstance(collectors, dict):
        raise ConfigError("'collectors' must be a table")

    for cname, cval in collectors.items():
        if not isinstance(cval, dict):
            raise ConfigError(f"collector {cname!r} must be a table")
        ctype = cval.get("type")
        if ctype is None:
            raise ConfigError(f"collector {cname!r} is missing required key 'type'")
        if ctype not in known_collectors:
            raise ConfigError(
                f"collector {cname!r} has unknown type {ctype!r}; "
                f"available: {sorted(known_collectors)}"
            )

    alerters = cfg.get("alerters", {})
    if not isinstance(alerters, dict):
        raise ConfigError("'alerters' must be a table")

    for aname, aval in alerters.items():
        if not isinstance(aval, dict):
            raise ConfigError(f"alerter {aname!r} must be a table")
        atype = aval.get("type")
        if atype is None:
            raise ConfigError(f"alerter {aname!r} is missing required key 'type'")
        if atype not in known_alerters:
            raise ConfigError(
                f"alerter {aname!r} has unknown type {atype!r}; "
                f"available: {sorted(known_alerters)}"
            )

    interval = cfg.get("interval")
    if interval is not None and (not isinstance(interval, (int, float)) or interval <= 0):
        raise ConfigError("'interval' must be a positive number")
