"""Configuration loading and validation for driftwatch."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore

from driftwatch.collectors import list_collectors
from driftwatch.alerters import list_alerters

_KNOWN_COLLECTORS = set(list_collectors())
_KNOWN_ALERTERS = set(list_alerters())


class ConfigError(ValueError):
    """Raised when the driftwatch configuration is invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML or JSON config file and return the parsed dict."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(raw)
    else:
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a YAML/JSON mapping at the top level.")
    return data


def validate_config(config: dict[str, Any]) -> None:
    """Validate the top-level structure of a driftwatch config dict.

    Raises
    ------
    ConfigError
        On any structural or type violation.
    """
    if not isinstance(config, dict):
        raise ConfigError("Config must be a dict.")

    if "collectors" not in config:
        raise ConfigError("Config must contain a 'collectors' key.")

    collectors = config["collectors"]
    if not isinstance(collectors, list) or not collectors:
        raise ConfigError("'collectors' must be a non-empty list.")

    for i, col in enumerate(collectors):
        if not isinstance(col, dict):
            raise ConfigError(f"collectors[{i}] must be a dict.")
        if "type" not in col:
            raise ConfigError(f"collectors[{i}] is missing required key 'type'.")
        if col["type"] not in _KNOWN_COLLECTORS:
            raise ConfigError(
                f"collectors[{i}] has unknown type '{col['type']}'. "
                f"Known: {sorted(_KNOWN_COLLECTORS)}"
            )

    alerters = config.get("alerters", [])
    if not isinstance(alerters, list):
        raise ConfigError("'alerters' must be a list.")

    for i, al in enumerate(alerters):
        if not isinstance(al, dict):
            raise ConfigError(f"alerters[{i}] must be a dict.")
        if "type" not in al:
            raise ConfigError(f"alerters[{i}] is missing required key 'type'.")
        if al["type"] not in _KNOWN_ALERTERS:
            raise ConfigError(
                f"alerters[{i}] has unknown type '{al['type']}'. "
                f"Known: {sorted(_KNOWN_ALERTERS)}"
            )
