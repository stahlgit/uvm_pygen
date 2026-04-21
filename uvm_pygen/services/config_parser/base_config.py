"""Base class for configuration objects loaded from YAML files."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self

import yaml


class BaseConfiguration(ABC):
    """Base class for configuration objects loaded from YAML files."""

    def __init__(self, config_path: str | Path) -> None:
        """Initialize the configuration by loading and parsing the YAML file."""
        self.config_path = Path(config_path)
        self._raw_config: dict = {}
        self._init_extra_state()
        self._load()
        self._parse()

    def _init_extra_state(self) -> None:  # noqa: B027
        """Initialize subclass-specific instance state before _parse() is called.

        Override in subclasses that need extra attributes set up before parsing
        (e.g. interface_list in UVMConfiguration).
        """
        pass

    def _load(self) -> None:
        """Load raw YAML into _raw_config."""
        with open(self.config_path) as f:
            self._raw_config = yaml.safe_load(f)

    @abstractmethod
    def _parse(self) -> None:
        """Parse raw config dict into Pydantic model instances."""
        pass

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate configuration consistency.

        Returns:
            list[str]: Accumulated error messages. Empty list means valid.
        """
        pass

    @classmethod
    def from_dict(cls, raw: dict, source_label: str = "<in-memory>") -> Self:
        """Construct a DUTConfiguration from an already-loaded dict.

        This is used when the config comes from a unified YAML file that has
        already been read and split by ``config_resolver.split_unified_config``.

        Args:
            raw: Dict with the same structure as a DUT YAML file (``dut``, ``parameters``,
                ``enums``, ``ports``, … keys at the top level).
            source_label: Human-readable label used in error messages (e.g. the unified file path).

        Returns:
            DUTConfiguration: A new instance initialized from the provided dict.
        """
        instance = cls.__new__(cls)
        instance.config_path = Path(source_label)
        instance._raw_config = raw
        instance._init_extra_state()
        instance._parse()
        return instance

    @staticmethod
    def _get_aliased(raw: dict, aliases: list[str], default):
        """Return the first value from raw whose key appears in aliases, or default."""
        return next((raw[k] for k in aliases if k in raw), default)
