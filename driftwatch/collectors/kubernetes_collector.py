"""Collector that reads Kubernetes pod/deployment state via the k8s API."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class KubernetesCollector(BaseCollector):
    """Collect running pod and deployment state from a Kubernetes cluster."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._namespace: str = config.get("namespace", "default")
        self._name_pattern: Optional[str] = config.get("name_pattern")
        self._resource: str = config.get("resource", "pods")  # pods | deployments
        self._kubeconfig: Optional[str] = config.get("kubeconfig")
        self._context: Optional[str] = config.get("context")
        self._compiled: Optional[re.Pattern] = (
            re.compile(self._name_pattern) if self._name_pattern else None
        )

    def validate_config(self) -> None:
        if self._resource not in ("pods", "deployments"):
            raise ValueError(
                f"resource must be 'pods' or 'deployments', got '{self._resource}'"
            )
        if self._name_pattern:
            try:
                re.compile(self._name_pattern)
            except re.error as exc:
                raise ValueError(f"invalid name_pattern regex: {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        from kubernetes import client, config as k8s_config  # type: ignore

        if self._kubeconfig:
            k8s_config.load_kube_config(
                config_file=self._kubeconfig, context=self._context
            )
        else:
            try:
                k8s_config.load_incluster_config()
            except k8s_config.ConfigException:
                k8s_config.load_kube_config(context=self._context)

        data: Dict[str, Any] = {}

        if self._resource == "pods":
            v1 = client.CoreV1Api()
            items: List[Any] = v1.list_namespaced_pod(self._namespace).items
            for pod in items:
                name: str = pod.metadata.name
                if self._compiled and not self._compiled.search(name):
                    continue
                phase = pod.status.phase or "Unknown"
                ready_containers = sum(
                    1
                    for cs in (pod.status.container_statuses or [])
                    if cs.ready
                )
                total_containers = len(pod.spec.containers or [])
                data[name] = {
                    "phase": phase,
                    "ready": f"{ready_containers}/{total_containers}",
                    "node": pod.spec.node_name or "",
                }
        else:
            apps_v1 = client.AppsV1Api()
            items = apps_v1.list_namespaced_deployment(self._namespace).items
            for dep in items:
                name = dep.metadata.name
                if self._compiled and not self._compiled.search(name):
                    continue
                spec_replicas = dep.spec.replicas or 0
                ready_replicas = dep.status.ready_replicas or 0
                data[name] = {
                    "desired": spec_replicas,
                    "ready": ready_replicas,
                    "image": dep.spec.template.spec.containers[0].image
                    if dep.spec.template.spec.containers
                    else "",
                }

        return ConfigSnapshot(source=f"kubernetes:{self._resource}", data=data)
