"""Tests for TerraformCollector."""
from __future__ import annotations

import json
import pytest

from driftwatch.collectors.terraform_collector import TerraformCollector


_STATE = {
    "version": 4,
    "terraform_version": "1.6.0",
    "resources": [
        {
            "mode": "managed",
            "type": "aws_instance",
            "name": "web",
            "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
            "instances": [{"attributes": {"instance_type": "t3.micro", "ami": "ami-123"}}],
        },
        {
            "mode": "managed",
            "type": "aws_s3_bucket",
            "name": "assets",
            "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
            "instances": [{"attributes": {"bucket": "my-assets", "acl": "private"}}],
        },
    ],
}


@pytest.fixture()
def state_file(tmp_path):
    p = tmp_path / "terraform.tfstate"
    p.write_text(json.dumps(_STATE), encoding="utf-8")
    return str(p)


def _make_collector(state_files, **kwargs):
    cfg = {"name": "tf", "state_files": state_files, **kwargs}
    return TerraformCollector(cfg)


def test_validate_config_ok(state_file):
    c = _make_collector([state_file])
    c.validate_config()  # should not raise


def test_validate_config_empty_state_files_raises():
    with pytest.raises(ValueError, match="state_files"):
        _make_collector([]).validate_config()


def test_validate_config_bad_pattern_raises(state_file):
    with pytest.raises(ValueError, match="invalid resource_pattern"):
        _make_collector([state_file], resource_pattern="[bad").validate_config()


def test_collect_returns_all_resources(state_file):
    c = _make_collector([state_file])
    snap = c.collect()
    assert "aws_instance.web" in snap.data
    assert "aws_s3_bucket.assets" in snap.data


def test_collect_with_resource_pattern(state_file):
    c = _make_collector([state_file], resource_pattern=r"^aws_instance")
    snap = c.collect()
    assert "aws_instance.web" in snap.data
    assert "aws_s3_bucket.assets" not in snap.data


def test_collect_attributes_present(state_file):
    c = _make_collector([state_file])
    snap = c.collect()
    assert snap.data["aws_instance.web"]["attributes"]["instance_type"] == "t3.micro"


def test_collect_include_meta(state_file):
    c = _make_collector([state_file], include_meta=True)
    snap = c.collect()
    entry = snap.data["aws_instance.web"]
    assert entry["mode"] == "managed"
    assert "provider" in entry


def test_collect_missing_file_returns_error():
    c = _make_collector(["/nonexistent/terraform.tfstate"])
    snap = c.collect()
    assert snap.data["/nonexistent/terraform.tfstate"]["error"] == "state_file_not_found"


def test_collect_invalid_json_returns_error(tmp_path):
    bad = tmp_path / "bad.tfstate"
    bad.write_text("not-json", encoding="utf-8")
    c = _make_collector([str(bad)])
    snap = c.collect()
    assert "error" in snap.data[str(bad)]


def test_collect_snapshot_source_name(state_file):
    c = _make_collector([state_file])
    snap = c.collect()
    assert snap.source == "tf"
