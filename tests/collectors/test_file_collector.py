"""Tests for FileCollector."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from driftwatch.collectors.file_collector import FileCollector


@pytest.fixture()
def tmp_file(tmp_path: Path) -> Path:
    f = tmp_path / "config.cfg"
    f.write_text("key=value\n")
    return f


def test_collect_existing_file_has_metadata(tmp_file: Path) -> None:
    collector = FileCollector({"paths": [str(tmp_file)]})
    snapshot = collector.collect()
    meta = snapshot.data[str(tmp_file)]
    assert meta["exists"] is True
    assert meta["size"] == tmp_file.stat().st_size
    assert "mtime" in meta


def test_collect_existing_file_checksum_default(tmp_file: Path) -> None:
    collector = FileCollector({"paths": [str(tmp_file)]})
    snapshot = collector.collect()
    meta = snapshot.data[str(tmp_file)]
    expected = hashlib.sha256(tmp_file.read_bytes()).hexdigest()
    assert meta["checksum"] == expected


def test_collect_checksum_disabled(tmp_file: Path) -> None:
    collector = FileCollector({"paths": [str(tmp_file)], "checksum": False})
    snapshot = collector.collect()
    assert "checksum" not in snapshot.data[str(tmp_file)]


def test_collect_missing_file_returns_not_exists(tmp_path: Path) -> None:
    missing = str(tmp_path / "ghost.cfg")
    collector = FileCollector({"paths": [missing]})
    snapshot = collector.collect()
    assert snapshot.data[missing] == {"exists": False}


def test_collect_multiple_paths(tmp_path: Path) -> None:
    files = [tmp_path / f"f{i}.txt" for i in range(3)]
    for f in files:
        f.write_text(f"content {f.name}")
    paths = [str(f) for f in files]
    collector = FileCollector({"paths": paths})
    snapshot = collector.collect()
    assert set(snapshot.data.keys()) == set(paths)
    assert all(snapshot.data[p]["exists"] for p in paths)


def test_snapshot_source_is_file(tmp_file: Path) -> None:
    collector = FileCollector({"paths": [str(tmp_file)]})
    assert collector.collect().source == "file"


def test_validate_config_missing_paths_raises() -> None:
    with pytest.raises(ValueError, match="paths"):
        FileCollector({})


def test_validate_config_paths_not_list_raises() -> None:
    with pytest.raises(TypeError, match="list"):
        FileCollector({"paths": "/etc/hosts"})


def test_validate_config_bad_algorithm_raises() -> None:
    with pytest.raises(ValueError, match="algorithm"):
        FileCollector({"paths": [], "algorithm": "rot13"})


def test_custom_algorithm_md5(tmp_file: Path) -> None:
    collector = FileCollector({"paths": [str(tmp_file)], "algorithm": "md5"})
    snapshot = collector.collect()
    expected = hashlib.md5(tmp_file.read_bytes()).hexdigest()
    assert snapshot.data[str(tmp_file)]["checksum"] == expected
