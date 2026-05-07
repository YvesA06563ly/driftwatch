"""Registry integration tests for GitCollector."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from driftwatch.collectors import get_collector, list_collectors
from driftwatch.collectors.git_collector import GitCollector

REPO = "/tmp/fake-repo"


def test_git_in_list_collectors():
    assert "git" in list_collectors()


def test_get_collector_returns_git_instance():
    collector = get_collector({"type": "git", "repos": [REPO]})
    assert isinstance(collector, GitCollector)


def test_get_collector_git_invalid_config_raises():
    with pytest.raises(ValueError, match="repos"):
        get_collector({"type": "git", "repos": []})


def test_get_collector_git_collect_via_registry():
    collector = get_collector(
        {"type": "git", "repos": [REPO], "include_remotes": False}
    )

    def _fake_run(args, cwd):
        key = args[1] if len(args) > 1 else args[0]
        return {"rev-parse": "cafebabe", "status": ""}.get(key)

    collector._run = _fake_run  # type: ignore[method-assign]
    snap = collector.collect()
    assert snap.data[REPO]["commit"] == "cafebabe"
