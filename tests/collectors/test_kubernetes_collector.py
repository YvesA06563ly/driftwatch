"""Tests for KubernetesCollector."""
from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors.kubernetes_collector import KubernetesCollector


def _make_pod(
    name: str,
    phase: str = "Running",
    ready: int = 1,
    total: int = 1,
    node: str = "node-1",
) -> Any:
    cs = SimpleNamespace(ready=True)
    container = SimpleNamespace()
    return SimpleNamespace(
        metadata=SimpleNamespace(name=name),
        status=SimpleNamespace(
            phase=phase,
            container_statuses=[cs] * ready,
        ),
        spec=SimpleNamespace(node_name=node, containers=[container] * total),
    )


def _make_deployment(
    name: str, desired: int = 2, ready: int = 2, image: str = "nginx:latest"
) -> Any:
    container = SimpleNamespace(image=image)
    return SimpleNamespace(
        metadata=SimpleNamespace(name=name),
        status=SimpleNamespace(ready_replicas=ready),
        spec=SimpleNamespace(
            replicas=desired,
            template=SimpleNamespace(
                spec=SimpleNamespace(containers=[container])
            ),
        ),
    )


@pytest.fixture()
def patched_k8s(monkeypatch):
    """Patch kubernetes client and config loader."""
    mock_k8s = MagicMock()
    monkeypatch.setitem(
        __import__("sys").modules, "kubernetes", mock_k8s
    )
    monkeypatch.setitem(
        __import__("sys").modules, "kubernetes.client", mock_k8s.client
    )
    monkeypatch.setitem(
        __import__("sys").modules, "kubernetes.config", mock_k8s.config
    )
    return mock_k8s


def _make_collector(cfg: Dict[str, Any]) -> KubernetesCollector:
    c = KubernetesCollector(cfg)
    c.validate_config()
    return c


def test_validate_config_ok():
    c = KubernetesCollector({"resource": "pods", "namespace": "kube-system"})
    c.validate_config()  # should not raise


def test_validate_config_bad_resource_raises():
    c = KubernetesCollector({"resource": "services"})
    with pytest.raises(ValueError, match="resource must be"):
        c.validate_config()


def test_validate_config_bad_pattern_raises():
    c = KubernetesCollector({"name_pattern": "[invalid"})
    with pytest.raises(ValueError, match="invalid name_pattern regex"):
        c.validate_config()


def test_collect_pods_no_filter(patched_k8s):
    pods = [_make_pod("api-abc"), _make_pod("worker-xyz")]
    patched_k8s.client.CoreV1Api.return_value.list_namespaced_pod.return_value.items = pods
    patched_k8s.config.ConfigException = Exception

    c = _make_collector({"resource": "pods", "namespace": "default"})
    with patch.object(c, "collect", wraps=c.collect):
        snap = c.collect()

    assert "api-abc" in snap.data
    assert snap.data["api-abc"]["phase"] == "Running"
    assert snap.source == "kubernetes:pods"


def test_collect_pods_with_name_pattern(patched_k8s):
    pods = [_make_pod("api-abc"), _make_pod("worker-xyz")]
    patched_k8s.client.CoreV1Api.return_value.list_namespaced_pod.return_value.items = pods
    patched_k8s.config.ConfigException = Exception

    c = _make_collector({"resource": "pods", "name_pattern": "^api"})
    snap = c.collect()

    assert "api-abc" in snap.data
    assert "worker-xyz" not in snap.data


def test_collect_deployments(patched_k8s):
    deps = [_make_deployment("frontend", desired=3, ready=3)]
    patched_k8s.client.AppsV1Api.return_value.list_namespaced_deployment.return_value.items = deps
    patched_k8s.config.ConfigException = Exception

    c = _make_collector({"resource": "deployments", "namespace": "prod"})
    snap = c.collect()

    assert "frontend" in snap.data
    assert snap.data["frontend"]["desired"] == 3
    assert snap.data["frontend"]["ready"] == 3
    assert snap.source == "kubernetes:deployments"
