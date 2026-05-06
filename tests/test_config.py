"""Tests for driftwatch.config."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftwatch.config import ConfigError, load_config, validate_config


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

def test_validate_requires_collectors_key():
    with pytest.raises(ConfigError, match="collectors"):
        validate_config({})


def test_validate_non_dict_raises():
    with pytest.raises(ConfigError, match="mapping"):
        validate_config(["not", "a", "dict"])  # type: ignore[arg-type]


def test_validate_unknown_collector_type():
    with pytest.raises(ConfigError, match="unknown type"):
        validate_config({"collectors": [{"type": "banana"}]})


def test_validate_collector_missing_type():
    with pytest.raises(ConfigError, match="missing 'type'"):
        validate_config({"collectors": [{}]})


def test_validate_unknown_alerter_type():
    with pytest.raises(ConfigError, match="unknown type"):
        validate_config({"collectors": [], "alerters": [{"type": "carrier_pigeon"}]})


def test_validate_alerter_missing_type():
    with pytest.raises(ConfigError, match="missing 'type'"):
        validate_config({"collectors": [], "alerters": [{}]})


def test_validate_valid_config_passes():
    validate_config(
        {
            "collectors": [{"type": "env", "options": {"prefix": "APP_"}}],
            "alerters": [{"type": "log"}],
        }
    )


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_missing_file(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.json")


def test_load_config_unsupported_extension(tmp_path: Path):
    p = tmp_path / "config.toml"
    p.write_text("[collectors]\n")
    with pytest.raises(ConfigError, match="Unsupported"):
        load_config(p)


def test_load_config_valid_json(tmp_path: Path):
    cfg = {"collectors": [{"type": "env"}]}
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    result = load_config(p)
    assert result["collectors"][0]["type"] == "env"
