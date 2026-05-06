"""Configuration loading and validation for driftwatch."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from driftwatch.collectors import list_collectors
from driftwatch.alerters import list_alerters

_VALID_COLLECTORS = set(list_collectors())
_VALID_ALERTERS = set(list_alerters())


class ConfigError(Exception):
    """Raised when the driftwatch configuration is invalid."""


def load_config(path: str) -> Dict[str, Any]:
    """Load a YAML or JSON config file and return the parsed dict."""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {path}")
    raw = p.read_text(encoding="utf-8")
    try:
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
    except Exception as exc:
        raise ConfigError(f"Failed to parse config file '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a YAML/JSON object at the top level.")
    validate_config(data)
    return data


def validate_config(config: Dict[str, Any]) -> None:
    """Validate the top-level driftwatch configuration dict.

    Raises
    ------
    ConfigError
        On any structural or semantic problem.
    """
    if not isinstance(config, dict):
        raise ConfigError("Configuration must be a mapping.")

    if "collectors" not in config:
        raise ConfigError("Configuration must contain a 'collectors' key.")

    collectors = config["collectors"]
    if not isinstance(collectors, list):
        raise ConfigError("'collectors' must be a list.")

    for idx, col in enumerate(collectors):
        if not isinstance(col, dict):
            raise ConfigError(f"collectors[{idx}] must be a mapping.")
        if "type" not in col:
            raise ConfigError(f"collectors[{idx}] is missing required 'type' field.")
        if col["type"] not in _VALID_COLLECTORS:
            raise ConfigError(
                f"collectors[{idx}] has unknown type '{col['type']}'. "
                f"Valid types: {sorted(_VALID_COLLECTORS)}"
            )

    alerters = config.get("alerters", [])
    if not isinstance(alerters, list):
        raise ConfigError("'alerters' must be a list.")

    for idx, alt in enumerate(alerters):
        if not isinstance(alt, dict):
            raise ConfigError(f"alerters[{idx}] must be a mapping.")
        if "type" not in alt:
            raise ConfigError(f"alerters[{idx}] is missing required 'type' field.")
        if alt["type"] not in _VALID_ALERTERS:
            raise ConfigError(
                f"alerters[{idx}] has unknown type '{alt['type']}'. "
                f"Valid types: {sorted(_VALID_ALERTERS)}"
            )
