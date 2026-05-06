"""Load and validate DriftWatch YAML/JSON configuration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

_REQUIRED_TOP_KEYS = ("collectors",)
_VALID_COLLECTOR_TYPES = {"env", "file", "process"}
_VALID_ALERTER_TYPES = {"log", "webhook"}


class ConfigError(ValueError):
    """Raised when configuration is invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load configuration from a YAML or JSON file."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        if not _YAML_AVAILABLE:
            raise ConfigError("PyYAML is required to load YAML configs (pip install pyyaml).")
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise ConfigError(f"Unsupported config format: {suffix}")

    validate_config(data)
    return data


def validate_config(data: dict[str, Any]) -> None:
    """Validate top-level structure and collector/alerter entries."""
    if not isinstance(data, dict):
        raise ConfigError("Config must be a mapping.")

    for key in _REQUIRED_TOP_KEYS:
        if key not in data:
            raise ConfigError(f"Missing required config key: '{key}'")

    for i, entry in enumerate(data.get("collectors", [])):
        if "type" not in entry:
            raise ConfigError(f"collectors[{i}] missing 'type' field.")
        if entry["type"] not in _VALID_COLLECTOR_TYPES:
            raise ConfigError(
                f"collectors[{i}] unknown type '{entry['type']}'. "
                f"Valid: {sorted(_VALID_COLLECTOR_TYPES)}"
            )

    for i, entry in enumerate(data.get("alerters", [])):
        if "type" not in entry:
            raise ConfigError(f"alerters[{i}] missing 'type' field.")
        if entry["type"] not in _VALID_ALERTER_TYPES:
            raise ConfigError(
                f"alerters[{i}] unknown type '{entry['type']}'. "
                f"Valid: {sorted(_VALID_ALERTER_TYPES)}"
            )
