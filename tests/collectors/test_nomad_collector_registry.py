"""Registry integration tests for NomadCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors


def _make_response(jobs: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = jobs
    resp.raise_for_status.return_value = None
    return resp


def test_nomad_in_list_collectors():
    assert "nomad" in list_collectors()


def test_get_collector_returns_nomad_instance():
    from driftwatch.collectors.nomad_collector import NomadCollector

    c = get_collector("nomad", {"url": "http://localhost:4646"})
    assert isinstance(c, NomadCollector)


def test_get_collector_nomad_invalid_pattern_raises():
    with pytest.raises((ValueError, Exception)):
        get_collector("nomad", {"url": "http://localhost:4646", "job_pattern": "[bad"})


def test_get_collector_nomad_collect_via_registry():
    c = get_collector("nomad", {"url": "http://nomad.example.com:4646"})
    with patch("driftwatch.collectors.nomad_collector.requests.get") as mock_get:
        mock_get.return_value = _make_response(
            [{"ID": "my-service", "Status": "running", "Type": "service", "Namespace": "default"}]
        )
        snap = c.collect()
    assert "my-service" in snap.data
    assert snap.data["my-service"]["status"] == "running"
