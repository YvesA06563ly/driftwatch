"""Integration tests: DockerCollector through the collector registry."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors


def test_docker_in_list_collectors():
    assert "docker" in list_collectors()


def test_get_collector_returns_docker_instance():
    from driftwatch.collectors.docker_collector import DockerCollector

    col = get_collector("docker", {})
    assert isinstance(col, DockerCollector)


def test_get_collector_docker_invalid_pattern_raises():
    with pytest.raises(ValueError):
        col = get_collector("docker", {"name_pattern": r"[bad"})
        col.validate_config()


def test_get_collector_docker_collect_via_registry():
    containers = []
    mock_client = MagicMock()
    mock_client.containers.list.return_value = containers
    with patch("driftwatch.collectors.docker_collector.docker") as mock_docker:
        mock_docker.from_env.return_value = mock_client
        col = get_collector("docker", {})
        snap = col.collect()
    assert snap.data == {}
    assert snap.source == "docker"
