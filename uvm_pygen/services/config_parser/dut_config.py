"""DUT Configuration Parser and Model."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from uvm_pygen.models.config_schema.dut_dataclass import (
    DUTInfo,
    EnumType,
    EnumValue,
    Parameter,
    Port,
)


class DUTConfiguration:
    """DUT Configuration Model - Single source of truth for DUT settings.

    Responsible for loading, parsing, and validating the DUT YAML config.
    Pydantic models handle per-field type coercion and validation on construction;
    this class handles cross-object consistency checks that require the full
    parsed state (enum resolution, etc.).
    """

    def __init__(self, config_path: str | Path) -> None:
        """Initialize DUT configuration from YAML file.

        Args:
            config_path: Path to the DUT YAML configuration file.
        """
        self.config_path = Path(config_path)
        self._raw_config: dict = {}

        self._load()
        self._parse()

    @classmethod
    def from_dict(cls, raw: dict, source_label: str = "<in-memory>") -> DUTConfiguration:
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

        instance._parse()
        return instance

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Validate configuration consistency.

        Performs cross-object checks that cannot be expressed inside a single
        Pydantic model:
          - Enum references on ports are resolved to live EnumType objects.

        Returns:
            list[str]: Accumulated error messages. Empty list means valid.
        """
        errors: list[str] = []
        errors.extend(self._resolve_port_enums())
        return errors

    def get_enum(self, enum_name: str) -> EnumType | None:
        """Get enum by name.

        Args:
            enum_name: Name of the enum to retrieve.

        Returns:
            EnumType | None: The enum type if found, None otherwise.
        """
        return self.enums.get(enum_name)

    def get_port(self, port_name: str) -> Port | None:
        """Get port by name.

        Args:
            port_name: Name of the port to retrieve.

        Returns:
            Port | None: The port if found, None otherwise.
        """
        for port in self.ports:
            if port.name == port_name:
                return port
        return None

    def get_signal_ports(self) -> list[Port]:
        """Get all non-clock, non-reset ports.

        Returns:
            list[Port]: List of signal ports.
        """
        return [p for p in self.ports if not p.is_clock and not p.is_reset]

    def get_clock_ports(self) -> list[Port]:
        """Get all clock ports.

        Returns:
            list[Port]: List of ports marked as clock.
        """
        return [p for p in self.ports if p.is_clock]

    def get_reset_ports(self) -> list[Port]:
        """Get all reset ports.

        Returns:
            list[Port]: List of ports marked as reset.
        """
        return [p for p in self.ports if p.is_reset]

    def resolve_width(self, width: Any) -> int:
        """Resolve width — int, parameter reference, or bus string like '(7:0)'.

        Note: arithmetic expressions such as '(DATA_WIDTH-1:0)' are not supported.

        Args:
            width: Width as int, parameter name, or bus notation string.

        Returns:
            int: The resolved width value.

        Raises:
            TypeError: If width is not int or str.
            ValueError: If width cannot be resolved or contains unsupported arithmetic.
        """
        if isinstance(width, int):
            return width

        if not isinstance(width, str):
            raise TypeError(f"Width must be int or str, got {type(width)}")

        # (MSB:LSB) or [MSB:LSB]
        match = re.match(r"\s*[\[\(](?P<msb>\w+)\s*:\s*(?P<lsb>\w+)[\]\)]\s*", width)
        if match:
            msb_str, lsb_str = match.group("msb"), match.group("lsb")
            if msb_str.isdigit() and lsb_str.isdigit():
                return int(msb_str) - int(lsb_str) + 1
            raise ValueError(f"Arithmetic in bus width not supported: {width}")

        # Parameter reference
        for param in self.parameters:
            if param.name == width:
                return param.value

        raise ValueError(f"Cannot resolve width: {width}")

    # -------------------------------------------------------------------------
    # Private — loading & parsing
    # -------------------------------------------------------------------------

    def _load(self) -> None:
        """Load raw YAML into _raw_config."""
        with open(self.config_path) as f:
            self._raw_config = yaml.safe_load(f)

    def _parse(self) -> None:
        """Parse raw config dict into Pydantic model instances.

        Pydantic raises ValidationError here if any field has a wrong type or
        value, giving you a precise per-field error message immediately on load
        rather than a cryptic KeyError/AttributeError later in generation.

        Raises:
            ValueError: If validation fails for DUT info, parameters, enums, or ports.
        """
        source = str(self.config_path)

        try:
            self.dut_info = DUTInfo(**self._raw_config["dut"])
        except ValidationError as exc:
            raise ValueError(f"DUT info validation failed in '{source}':\n{exc}") from exc

        # Parameters
        try:
            self.parameters: list[Parameter] = [Parameter(**p) for p in self._raw_config.get("parameters", [])]
        except ValidationError as exc:
            raise ValueError(f"Parameter validation failed in '{source}':\n{exc}") from exc

        # Enums
        self.enums: dict[str, EnumType] = {}
        for enum_name, enum_data in self._raw_config.get("enums", {}).items():
            try:
                values = [EnumValue(**v) for v in enum_data["values"]]
                self.enums[enum_name] = EnumType(name=enum_name, type=enum_data["type"], values=values)
            except ValidationError as exc:
                raise ValueError(f"Enum '{enum_name}' validation failed in '{source}':\n{exc}") from exc

        # Ports — strip internal key 'enum_def' if accidentally present in YAML
        self.ports: list[Port] = []
        for raw_port in self._raw_config.get("ports", []):
            raw_port.pop("enum_def", None)
            try:
                self.ports.append(Port(**raw_port))
            except ValidationError as exc:
                name = raw_port.get("name", "<unknown>")
                raise ValueError(f"Port '{name}' validation failed in '{source}':\n{exc}") from exc

        # Behavior / operand selection
        behavior = self._raw_config.get("behavior", {})
        self.operand_selection: dict = behavior.get("operand_selection", {})

    # -------------------------------------------------------------------------
    # Private — cross-object validation helpers
    # -------------------------------------------------------------------------

    def _resolve_port_enums(self) -> list[str]:
        """Link enum_name references on ports to live EnumType objects.

        Returns:
            list[str]: Errors for any unresolved enum reference.
        """
        errors: list[str] = []
        for port in self.ports:
            if not port.enum_name:
                continue
            if port.enum_name in self.enums:
                object.__setattr__(port, "enum_def", self.enums[port.enum_name])
            else:
                errors.append(f"Port '{port.name}' references unknown enum: '{port.enum_name}'")
        return errors

