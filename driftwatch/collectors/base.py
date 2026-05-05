"""Base collector interface for infrastructure configuration sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ConfigSnapshot:
    """Represents a point-in-time snapshot of a configuration value."""

    source: str
    key: str
    value: Any
    collected_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConfigSnapshot):
            return NotImplemented
        return self.source == other.source and self.key == other.key and self.value == other.value


class BaseCollector(ABC):
    """Abstract base class all collectors must implement."""

    def __init__(self, name: str, config: dict | None = None) -> None:
        self.name = name
        self.config = config or {}

    @abstractmethod
    def collect(self) -> list[ConfigSnapshot]:
        """Collect current configuration snapshots from the source.

        Returns:
            A list of ConfigSnapshot objects representing current state.
        """
        raise NotImplementedError

    def validate_config(self) -> bool:
        """Validate that the collector has the required configuration.

        Override in subclasses to enforce required config keys.
        """
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
