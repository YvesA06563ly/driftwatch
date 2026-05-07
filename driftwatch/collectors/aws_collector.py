"""AWS SSM Parameter Store collector for driftwatch."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class AwsCollector(BaseCollector):
    """Collect parameter values from AWS SSM Parameter Store."""

    name = "aws"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._path_prefix: str = config.get("path_prefix", "/")
        self._parameters: List[str] = config.get("parameters", [])
        self._pattern: Optional[str] = config.get("pattern")
        self._region: str = config.get("region", "us-east-1")
        self._recursive: bool = bool(config.get("recursive", True))
        self._decrypt: bool = bool(config.get("decrypt", True))
        self._compiled: Optional[re.Pattern] = (
            re.compile(self._pattern) if self._pattern else None
        )

    def validate_config(self) -> None:
        if not self._path_prefix and not self._parameters:
            raise ValueError(
                "aws collector requires at least one of 'path_prefix' or 'parameters'"
            )
        if self._pattern:
            try:
                re.compile(self._pattern)
            except re.error as exc:
                raise ValueError(f"invalid pattern '{self._pattern}': {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "boto3 is required for AwsCollector: pip install boto3"
            ) from exc

        client = boto3.client("ssm", region_name=self._region)
        data: Dict[str, str] = {}

        if self._parameters:
            resp = client.get_parameters(
                Names=self._parameters, WithDecryption=self._decrypt
            )
            for param in resp.get("Parameters", []):
                data[param["Name"]] = param["Value"]
        else:
            paginator = client.get_paginator("get_parameters_by_path")
            pages = paginator.paginate(
                Path=self._path_prefix,
                Recursive=self._recursive,
                WithDecryption=self._decrypt,
            )
            for page in pages:
                for param in page.get("Parameters", []):
                    name: str = param["Name"]
                    if self._compiled and not self._compiled.search(name):
                        continue
                    data[name] = param["Value"]

        return ConfigSnapshot(source="aws", data=data)
