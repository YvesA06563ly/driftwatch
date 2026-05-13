"""Tests for NomadCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.nomad_collector import NomadCollector


def _make_job(job_id: str, status: str = "running", job_type: str = "service") -> dict:
    return {"ID": job_id, "Status": status, "Type": job_type, "Namespace": "default"}


def _make_response(jobs: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = jobs
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture()
def collector() -> NomadCollector:
    return NomadCollector({"url": "http://nomad.local:4646"})


@pytest.fixture()
def patched_get(collector):
    with patch("driftwatch.collectors.nomad_collector.requests.get") as mock_get:
        yield mock_get


def test_validate_config_ok():
    c = NomadCollector({"url": "http://nomad.local:4646", "job_pattern": "web-.*"})
    c.validate_config()  # should not raise


def test_validate_config_bad_pattern_raises():
    c = NomadCollector({"url": "http://nomad.local:4646", "job_pattern": "[invalid"})
    with pytest.raises(ValueError, match="invalid job_pattern"):
        c.validate_config()


def test_collect_no_filter_returns_all(collector, patched_get):
    patched_get.return_value = _make_response(
        [_make_job("api"), _make_job("worker", status="pending")]
    )
    snap = collector.collect()
    assert "api" in snap.data
    assert "worker" in snap.data
    assert snap.data["api"]["status"] == "running"
    assert snap.data["worker"]["status"] == "pending"


def test_collect_with_job_pattern(patched_get):
    c = NomadCollector({"url": "http://nomad.local:4646", "job_pattern": "^web-"})
    patched_get.return_value = _make_response(
        [_make_job("web-frontend"), _make_job("api-backend")]
    )
    snap = c.collect()
    assert "web-frontend" in snap.data
    assert "api-backend" not in snap.data


def test_collect_passes_token(patched_get):
    c = NomadCollector({"url": "http://nomad.local:4646", "token": "secret-token"})
    patched_get.return_value = _make_response([])
    c.collect()
    _, kwargs = patched_get.call_args
    assert kwargs["headers"]["X-Nomad-Token"] == "secret-token"


def test_collect_passes_namespace(patched_get):
    c = NomadCollector({"url": "http://nomad.local:4646", "namespace": "production"})
    patched_get.return_value = _make_response([])
    c.collect()
    _, kwargs = patched_get.call_args
    assert kwargs["params"]["namespace"] == "production"


def test_collect_snapshot_source_contains_url(collector, patched_get):
    patched_get.return_value = _make_response([])
    snap = collector.collect()
    assert "nomad:" in snap.source
    assert "nomad.local" in snap.source


def test_collect_empty_jobs_returns_empty_data(collector, patched_get):
    patched_get.return_value = _make_response([])
    snap = collector.collect()
    assert snap.data == {}


def test_collect_job_type_captured(collector, patched_get):
    patched_get.return_value = _make_response([_make_job("batch-job", job_type="batch")])
    snap = collector.collect()
    assert snap.data["batch-job"]["type"] == "batch"
