"""Collector that snapshots Redis configuration and info fields."""
from __future__ import annotations

import re
from typing import Any

try:
    import redis as redis_lib
except ImportError:  # pragma: no cover
    redis_lib = None  # type: ignore

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class RedisCollector(BaseCollector):
    """Collect Redis CONFIG GET and INFO fields as a snapshot.

    Config keys:
        url (str): Redis URL, e.g. ``redis://localhost:6379/0``.  Required.
        config_pattern (str): Glob pattern passed to CONFIG GET (default ``"*"``).
        info_sections (list[str]): INFO sections to include, e.g. ``["server", "replication"]``.
            Defaults to ``["server"]``.
        exclude_pattern (str | None): Regex; matching keys are dropped from the snapshot.
    """

    name = "redis"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._url: str = config.get("url", "redis://localhost:6379/0")
        self._config_pattern: str = config.get("config_pattern", "*")
        self._info_sections: list[str] = config.get("info_sections", ["server"])
        raw_exclude = config.get("exclude_pattern")
        self._exclude_re = re.compile(raw_exclude) if raw_exclude else None

    def validate_config(self) -> None:
        if not self._url:
            raise ValueError("RedisCollector requires a non-empty 'url'")
        if redis_lib is None:
            raise RuntimeError(
                "redis-py is not installed; run: pip install redis"
            )

    def collect(self) -> ConfigSnapshot:
        client = redis_lib.from_url(self._url, socket_connect_timeout=5)
        data: dict[str, str] = {}

        # CONFIG GET
        cfg = client.config_get(self._config_pattern)
        for k, v in cfg.items():
            data[f"config:{k}"] = str(v)

        # INFO sections
        for section in self._info_sections:
            info = client.info(section)
            for k, v in info.items():
                data[f"info:{section}:{k}"] = str(v)

        # Apply exclude filter
        if self._exclude_re:
            data = {k: v for k, v in data.items() if not self._exclude_re.search(k)}

        return ConfigSnapshot(source=self.name, data=data)
