"""Collector that captures environment variable configuration snapshots."""

import os
import re

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class EnvCollector(BaseCollector):
    """Collects environment variables matching a configurable prefix or pattern.

    Config keys:
        prefix (str): Only collect vars that start with this prefix.
        pattern (str): Regex pattern to match variable names (overrides prefix).
        exclude (list[str]): Variable names to explicitly exclude.
    """

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(name="env", config=config)
        self._pattern: re.Pattern | None = None
        if pattern := self.config.get("pattern"):
            self._pattern = re.compile(pattern)

    def validate_config(self) -> bool:
        if "pattern" in self.config:
            try:
                re.compile(self.config["pattern"])
            except re.error:
                return False
        return True

    def collect(self) -> list[ConfigSnapshot]:
        exclude: set[str] = set(self.config.get("exclude", []))
        prefix: str = self.config.get("prefix", "")
        snapshots: list[ConfigSnapshot] = []

        for key, value in os.environ.items():
            if key in exclude:
                continue
            if self._pattern:
                if not self._pattern.match(key):
                    continue
            elif prefix and not key.startswith(prefix):
                continue

            snapshots.append(
                ConfigSnapshot(
                    source=self.name,
                    key=key,
                    value=value,
                    metadata={"prefix": prefix, "pattern": self.config.get("pattern")},
                )
            )

        return snapshots
