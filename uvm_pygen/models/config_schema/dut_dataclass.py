"""DUT models for UVM testbench generation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from uvm_pygen.constants.uvm_enum import ActiveLevel, Direction


class DUTInfo(BaseModel):
    """Basic DUT information.

    Top-level YAML key: ``dut``  (required — its presence identifies a DUT config).
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={"yaml_section": "dut", "yaml_key": "dut", "required": True},
    )

    name: str
    entity_name: str  # for VHDL; ignored for SV/Verilog (defaults to name)
    ###NOTE: this feels redundant
    data_width: int
    output_width: int
    clock_period: int  # in ns
    ###
    reset_type: ActiveLevel
    language: str
    description: str | None = None

    @field_validator("data_width", "output_width", "clock_period", mode="before")
    @classmethod
    def must_be_positive(cls, v: Any, info) -> int:
        """Ensure that these fields are positive integers, even if provided as strings in YAML."""
        v = int(v)
        if v <= 0:
            raise ValueError(f"{info.field_name} must be a positive integer, got {v}")
        return v


class Parameter(BaseModel):
    """DUT parameter definition.

    Top-level YAML key: ``parameters``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "dut", "yaml_key": "parameters"},
    )

    name: str
    value: Any
    description: str | None = None


class EnumValue(BaseModel):
    """Single enum value — nested inside ``EnumType``, not a top-level YAML key."""

    name: str
    value: str
    description: str | None = None

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_string(cls, v: Any) -> str:
        """Automatically convert integers (like 0) from YAML into strings."""
        return str(v)


class EnumType(BaseModel):
    """Enumeration type definition.

    Top-level YAML key: ``enums``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "dut", "yaml_key": "enums"},
    )

    name: str
    type: str
    values: list[EnumValue]

    def get_value_by_name(self, name: str) -> str | None:
        """Get enum value by name."""
        for val in self.values:
            if val.name == name:
                return val.value
        return None

    def get_name_by_value(self, value: str) -> str | None:
        """Get enum name by value."""
        for val in self.values:
            if val.value == value:
                return val.name
        return None

    def get_all_names(self) -> list[str]:
        """Get all enum names."""
        return [val.name for val in self.values]


class Port(BaseModel):
    """DUT port definition.

    Top-level YAML key: ``ports``
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={"yaml_section": "dut", "yaml_key": "ports"},
    )

    name: str
    direction: Direction
    type: str  # e.g., "logic", "wire"
    width: Any

    description: str | None = None
    group: str | None = None  # e.g., "clock", "reset", "data", "control"

    is_clock: bool = False
    is_reset: bool = False
    active_level: ActiveLevel | None = None

    enum_name: str | None = None  # reference to EnumType name

    # Resolved post-load by DUTConfiguration.validate(); excluded from serialization
    enum_def: EnumType | None = Field(default=None, exclude=True)

    @field_validator("width", mode="before")
    @classmethod
    def coerce_width(cls, v: Any) -> Any:
        """Accept int, string integer, or bus expression string like '(7:0)'."""
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.strip().isdigit():
            return int(v.strip())
        # Bus expression strings are kept as-is; resolved later by DUTConfiguration
        return v

    @field_validator("active_level", mode="before")
    @classmethod
    def map_active_level_aliases(cls, v: Any) -> Any:
        """Map user-friendly shorthand to the strict ActiveLevel enum strings."""
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower == "high":
                return "active_high"
            if v_lower == "low":
                return "active_low"
        return v

    @field_validator("direction", mode="before")
    @classmethod
    def map_direction_aliases(cls, v: Any) -> Any:
        """Map user-friendly shorthands to the strict Direction enum strings."""
        if isinstance(v, str):
            v_norm = v.lower().strip()
            _aliases = {
                # INPUT
                "input": "input",
                "in": "input",
                "i": "input",
                # OUTPUT
                "output": "output",
                "out": "output",
                "o": "output",
                # INOUT
                "inout": "inout",
                "io": "inout",
                "bidi": "inout",
                "bidirectional": "inout",
            }
            mapped = _aliases.get(v_norm)
            if mapped is not None:
                return mapped
            # Let Pydantic raise a proper validation error for unknown values
        return v


class Constraints(BaseModel):
    """Constraint definition.

    Top-level YAML key: ``constraints``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "dut", "yaml_key": "constraints"},
    )

    name: str
    description: str
    constraint: str  # constraint itself
