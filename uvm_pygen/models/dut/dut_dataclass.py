"""DUT models for UVM testbench generation."""
from dataclasses import dataclass
from typing import Any

@dataclass
class DUTInfo:
    """Basic DUT information."""
    name: str
    data_width: int # TODO: create parser for (1:0) format
    output_width: int
    clock_period: int # in ns
    reset_type: str # e.g., "active_high", "active_low"
    language: str
    description: str | None = None


@dataclass
class Parameter:
    """DUT parameter definition."""
    name: str
    value: Any
    description: str | None = None
    
@dataclass
class EnumValue:
    """Single enum value."""
    name: str
    value: str
    description: str | None = None

@dataclass
class EnumType:
    """Enumeration type definition."""
    name: str
    type: str
    values: list[EnumValue]
    
    def get_value_by_name(self, name: str ) -> str | None:
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
    
    def get_all_names(self)-> list[str]:
        """Get all enum names."""
        return [val.name for val in self.values]
    
@dataclass
class Port:
    """DUT port definition."""
    name: str
    direction: str # e.g., "input", "output", "inout" #TODO: create enum or checker
    type: str # e.g., "logic", "wire"
    width: Any # TODO: create parser for (1:0) format or int also string reference (e.g., DATA_WIDTH)
    description: str | None = None
    group: str | None = None # e.g., "clock", "reset", "data", "control"
    is_clock: bool = False
    is_reset: bool = False
    active_level: str | None = None # e.g., "active_high", "active_low" --> could be enum | transformed to bool
    enum_type: EnumType | None = None # Reference to EnumType if port is of enum type 
    enum: EnumType | None = None # IS there possibility to combine this with enum_type? 

@dataclass
class OperationTiming:
    """Timing specification for operation."""
    latency: int # in clock cycles
    description: str | None = None
    multi_cycle: bool = False
    output_behavior: list[dict] | None = None 

@dataclass
class Operation:
    """DUT operation definition."""
    op: str
    formula: str # e.g., "A + B", "A & B"
    output_width: Any # TODO: create parser for (1:0) format or int also string reference (e.g., DATA_WIDTH)
    overflow: str | None = None 
    latency : int = 1
    notes: str | None = None
    implementation: str | None = None 

@dataclass
class Constraints:
    """Constraint definition."""
    name: str
    description: str
    constraint: str # constraint itself
    
