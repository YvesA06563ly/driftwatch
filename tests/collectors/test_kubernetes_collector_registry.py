"""Registry integration tests for KubernetesCollector."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftwatch.collectors import get_collector, list_collectors


def test_kubernetes_in_list_collectors():
    assert "kubernetes" in list_collectors()


def test_get_collector_returns_kubernetes_instance():
    from driftwatch.collectors.kubernetes_collector import KubernetesCollector

    c = get_collector("kubernetes", {"resource": "pods"})
    assert isinstance(c, KubernetesCollector)


def test_get_collector_kubernetes_invalid_resource_raises():
    with pytest.raises(ValueError, match="resource must be"):
        get_collector("kubernetes", {"resource": "configmaps"})


def test_get_collector_kubernetes_collect_via_registry():
    from types import SimpleNamespace

    mock_k8s = MagicMock()
    mock_k8s.config.ConfigException = Exception
    pod = SimpleNamespace(
        metadata=SimpleNamespace(name="nginx-abc"),
        status=SimpleNamespace(phase="Running", container_statuses=[]),
        spec=SimpleNamespace(node_name="node-1", containers=[SimpleNamespace()]),
    )
    mock_k8s.client.CoreV1Api.return_value.list_namespaced_pod.return_value.items = [pod]

    import sys

    sys.modules["kubernetes"] = mock_k8s
    sys.modules["kubernetes.client"] = mock_k8s.client
    sys.modules["kubernetes.config"] = mock_k8s.config

    try:
        c = get_collector("kubernetes", {"resource": "pods", "namespace": "default"})
        snap = c.collect()
        assert "nginx-abc" in snap.data
    finally:
        for mod in ("kubernetes", "kubernetes.client", "kubernetes.config"):
            sys.modules.pop(mod, None)
