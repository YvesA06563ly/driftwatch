"""Collector that reads Azure App Configuration / Key Vault secrets via the Azure SDK."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from driftwatch.collectors.base import BaseCollector, ConfigSnapshot


class AzureCollector(BaseCollector):
    """Collect key-value pairs from Azure App Configuration.

    Config keys:
        endpoint   (str)  – App Configuration endpoint URL (required)
        credential (str)  – 'default' (DefaultAzureCredential) or a connection string
        key_filter (str)  – optional glob/prefix passed to the SDK list call
        label      (str)  – optional label filter (default: no label filter)
        key_pattern (str) – optional regex applied client-side to key names
    """

    name = "azure"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self._endpoint: str = config.get("endpoint", "")
        self._credential_type: str = config.get("credential", "default")
        self._key_filter: Optional[str] = config.get("key_filter")
        self._label: Optional[str] = config.get("label")
        self._key_pattern: Optional[str] = config.get("key_pattern")
        self._pattern_re = (
            re.compile(self._key_pattern) if self._key_pattern else None
        )

    def validate_config(self) -> None:
        if not self._endpoint:
            raise ValueError("azure collector requires a non-empty 'endpoint'")
        if not self._endpoint.startswith(("https://", "http://")):
            raise ValueError("azure collector 'endpoint' must start with http(s)://")
        if self._key_pattern:
            try:
                re.compile(self._key_pattern)
            except re.error as exc:
                raise ValueError(f"azure collector invalid 'key_pattern': {exc}") from exc

    def collect(self) -> ConfigSnapshot:
        try:
            from azure.appconfiguration import AzureAppConfigurationClient  # type: ignore
            from azure.identity import DefaultAzureCredential  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "azure-appconfiguration and azure-identity packages are required"
            ) from exc

        if self._credential_type == "default":
            credential = DefaultAzureCredential()
            client = AzureAppConfigurationClient(self._endpoint, credential)
        else:
            client = AzureAppConfigurationClient.from_connection_string(self._credential_type)

        kwargs: Dict[str, Any] = {}
        if self._key_filter:
            kwargs["key_filter"] = self._key_filter
        if self._label:
            kwargs["label_filter"] = self._label

        data: Dict[str, Any] = {}
        for setting in client.list_configuration_settings(**kwargs):
            key = setting.key
            if self._pattern_re and not self._pattern_re.search(key):
                continue
            data[key] = setting.value

        return ConfigSnapshot(source=self.name, data=data)
