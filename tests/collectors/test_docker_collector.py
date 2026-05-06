"""Tests for DockerCollector."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.docker_collector import DockerCollector


def _make_container(name: str, short_id: str, status: str, image_tags: list[str], labels: dict) -> MagicMock:
    c = MagicMock()
    c.name = name
    c.short_id = short_id
    c.status = status
    c.labels = labels
    c.image.tags = image_tags
    c.image.short_id = "abc123"
    return c


@pytest.fixture()
def patched_docker():
    containers = [
        _make_container("web", "aaa", "running", ["nginx:latest"], {"env": "prod"}),
        _make_container("db", "bbb", "running", ["postgres:15"], {"env": "prod"}),
        _make_container("cache", "ccc", "exited", [], {"env": "dev"}),
    ]
    mock_client = MagicMock()
    mock_client.containers.list.return_value = containers
    with patch("driftwatch.collectors.docker_collector.docker") as mock_docker:
        mock_docker.from_env.return_value = mock_client
        yield mock_docker, mock_client, containers


def test_collect_no_filter_returns_all(patched_docker):
    _, client, _ = patched_docker
    col = DockerCollector({})
    snap = col.collect()
    assert set(snap.data.keys()) == {"web", "db", "cache"}


def test_collect_with_name_pattern(patched_docker):
    col = DockerCollector({"name_pattern": r"^(web|db)$"})
    snap = col.collect()
    assert "web" in snap.data
    assert "db" in snap.data
    assert "cache" not in snap.data


def test_collect_image_fallback_to_short_id(patched_docker):
    col = DockerCollector({})
    snap = col.collect()
    assert snap.data["cache"]["image"] == "abc123"


def test_collect_snapshot_source(patched_docker):
    col = DockerCollector({})
    snap = col.collect()
    assert snap.source == "docker"


def test_validate_config_bad_pattern_raises():
    col = DockerCollector({"name_pattern": r"[invalid"})
    with pytest.raises(ValueError, match="Invalid name_pattern"):
        col.validate_config()


def test_validate_config_bad_label_filter_raises():
    col = DockerCollector({"label_filter": "not-a-dict"})
    with pytest.raises(ValueError, match="label_filter"):
        col.validate_config()


def test_validate_config_ok_passes(patched_docker):
    col = DockerCollector({"name_pattern": r"web.*", "label_filter": {"env": "prod"}})
    col.validate_config()  # should not raise


def test_collect_passes_all_flag(patched_docker):
    _, client, _ = patched_docker
    col = DockerCollector({"all": True})
    col.collect()
    client.containers.list.assert_called_once_with(all=True, filters={})


def test_collect_client_closed(patched_docker):
    _, client, _ = patched_docker
    col = DockerCollector({})
    col.collect()
    client.close.assert_called_once()
