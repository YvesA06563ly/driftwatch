"""Registry integration tests for TerraformCollector."""
from __future__ import annotations

import json
import pytest

from driftwatch.collectors import get_collector, list_collectors


_STATE = {
    "version": 4,
    "resources": [
        {
            "mode": "managed",
            "type": "aws_vpc",
            "name": "main",
            "provider": "provider[\"registry.terraform.io/hashicorp/aws\"]",
            "instances": [{"attributes": {"cidr_block": "10.0.0.0/16"}}],
        }
    ],
}


def test_terraform_in_list_collectors():
    assert "terraform" in list_collectors()


def test_get_collector_returns_terraform_instance(tmp_path):
    sf = tmp_path / "terraform.tfstate"
    sf.write_text(json.dumps(_STATE), encoding="utf-8")
    from driftwatch.collectors.terraform_collector import TerraformCollector

    c = get_collector("terraform", {"name": "tf", "state_files": [str(sf)]})
    assert isinstance(c, TerraformCollector)


def test_get_collector_terraform_invalid_config_raises():
    with pytest.raises(ValueError, match="state_files"):
        get_collector("terraform", {"name": "tf", "state_files": []})


def test_get_collector_terraform_collect_via_registry(tmp_path):
    sf = tmp_path / "terraform.tfstate"
    sf.write_text(json.dumps(_STATE), encoding="utf-8")
    c = get_collector("terraform", {"name": "tf", "state_files": [str(sf)]})
    snap = c.collect()
    assert "aws_vpc.main" in snap.data
    assert snap.data["aws_vpc.main"]["attributes"]["cidr_block"] == "10.0.0.0/16"
