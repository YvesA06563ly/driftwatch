"""Collector that reads AWS CloudWatch metric alarms and emits their state."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class CloudWatchCollector(BaseCollector):
    """Collect AWS CloudWatch alarm states."""

    name = "cloudwatch"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._region: str = config.get("region", "us-east-1")
        self._alarm_prefix: Optional[str] = config.get("alarm_prefix")
        self._alarm_pattern: Optional[str] = config.get("alarm_pattern")
        self._state_filter: Optional[List[str]] = config.get("state_filter")
        self._profile: Optional[str] = config.get("aws_profile")

    def validate_config(self) -> None:
        if not self._region:
            raise ValueError("cloudwatch collector requires 'region'")
        if self._alarm_pattern:
            try:
                re.compile(self._alarm_pattern)
            except re.error as exc:
                raise ValueError(f"invalid alarm_pattern: {exc}") from exc
        if self._state_filter:
            valid = {"OK", "ALARM", "INSUFFICIENT_DATA"}
            bad = set(self._state_filter) - valid
            if bad:
                raise ValueError(f"invalid state_filter values: {bad}")

    def collect(self) -> ConfigSnapshot:
        if boto3 is None:  # pragma: no cover
            raise RuntimeError("boto3 is required for CloudWatchCollector")

        session_kwargs: Dict[str, Any] = {"region_name": self._region}
        if self._profile:
            session_kwargs["profile_name"] = self._profile
        session = boto3.Session(**session_kwargs)
        client = session.client("cloudwatch")

        paginator = client.get_paginator("describe_alarms")
        page_kwargs: Dict[str, Any] = {"AlarmTypes": ["MetricAlarm"]}
        if self._alarm_prefix:
            page_kwargs["AlarmNamePrefix"] = self._alarm_prefix
        if self._state_filter:
            page_kwargs["StateValue"] = self._state_filter[0] if len(self._state_filter) == 1 else None

        data: Dict[str, Any] = {}
        for page in paginator.paginate(**{k: v for k, v in page_kwargs.items() if v is not None}):
            for alarm in page.get("MetricAlarms", []):
                alarm_name: str = alarm["AlarmName"]
                if self._alarm_pattern and not re.search(self._alarm_pattern, alarm_name):
                    continue
                state = alarm["StateValue"]
                if self._state_filter and state not in self._state_filter:
                    continue
                data[alarm_name] = {
                    "state": state,
                    "metric": alarm.get("MetricName", ""),
                    "namespace": alarm.get("Namespace", ""),
                    "reason": alarm.get("StateReason", ""),
                }

        return ConfigSnapshot(source=self.name, data=data)
