"""Tests for GitCollector."""
from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.git_collector import GitCollector


REPO_A = "/repos/my-service"
REPO_B = "/repos/other-lib"


def _make_collector(extra: Optional[Dict[str, Any]] = None) -> GitCollector:
    cfg: Dict[str, Any] = {"type": "git", "repos": [REPO_A]}
    if extra:
        cfg.update(extra)
    c = GitCollector(cfg)
    c.validate_config()
    return c


def _patch_run(collector: GitCollector, mapping: Dict[str, Optional[str]]):
    """Patch _run so that the first CLI arg selects the return value."""
    def _fake_run(args, cwd):
        key = args[1] if len(args) > 1 else args[0]
        return mapping.get(key)
    collector._run = _fake_run  # type: ignore[method-assign]
    return collector


def test_validate_config_ok():
    c = GitCollector({"type": "git", "repos": [REPO_A, REPO_B]})
    c.validate_config()  # should not raise


def test_validate_config_missing_repos_raises():
    c = GitCollector({"type": "git"})
    with pytest.raises(ValueError, match="repos"):
        c.validate_config()


def test_validate_config_empty_repos_raises():
    c = GitCollector({"type": "git", "repos": []})
    with pytest.raises(ValueError, match="repos"):
        c.validate_config()


def test_validate_config_invalid_entry_raises():
    c = GitCollector({"type": "git", "repos": [""]})
    with pytest.raises(ValueError, match="invalid repo path"):
        c.validate_config()


def test_collect_basic_fields():
    c = _make_collector()
    _patch_run(c, {
        "rev-parse": "abc1234",
        "status": "",
        "remote": None,
    })
    snap = c.collect()
    assert snap.source == "git"
    assert REPO_A in snap.data
    entry = snap.data[REPO_A]
    assert entry["commit"] == "abc1234"
    assert entry["dirty"] is False


def test_collect_dirty_repo():
    c = _make_collector()
    _patch_run(c, {
        "rev-parse": "deadbeef",
        "status": " M some/file.py",
        "remote": None,
    })
    snap = c.collect()
    assert snap.data[REPO_A]["dirty"] is True


def test_collect_remotes_parsed():
    c = _make_collector({"include_remotes": True})
    run_results = {
        "rev-parse": "aaa",
        "status": "",
        "remote": "origin\thttps://github.com/org/repo.git (fetch)\norigin\thttps://github.com/org/repo.git (push)",
    }
    _patch_run(c, run_results)
    snap = c.collect()
    remotes = snap.data[REPO_A]["remotes"]
    assert remotes == {"origin": "https://github.com/org/repo.git"}


def test_collect_no_remotes_when_disabled():
    c = _make_collector({"include_remotes": False})
    _patch_run(c, {"rev-parse": "bbb", "status": ""})
    snap = c.collect()
    assert "remotes" not in snap.data[REPO_A]


def test_collect_submodules_when_enabled():
    c = _make_collector({"include_submodules": True, "include_remotes": False})
    run_results = {
        "rev-parse": "ccc",
        "status": "",
        "submodule": " abc1234 vendor/lib (v1.0)\n+def5678 vendor/other (v2.1)",
    }
    _patch_run(c, run_results)
    snap = c.collect()
    subs = snap.data[REPO_A]["submodules"]
    assert subs["vendor/lib"] == "abc1234"
    assert subs["vendor/other"] == "def5678"


def test_collect_multiple_repos():
    c = GitCollector({"type": "git", "repos": [REPO_A, REPO_B], "include_remotes": False})
    c.validate_config()
    _patch_run(c, {"rev-parse": "fff", "status": ""})
    snap = c.collect()
    assert REPO_A in snap.data
    assert REPO_B in snap.data
