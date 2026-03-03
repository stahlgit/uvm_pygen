"""Data Models for internal representation of UVM transactions."""

from dataclasses import dataclass

from uvm_pygen.constants.uvm_enum import Direction


@dataclass
class SvVariable:
    """Representation of a SystemVerilog variable for transaction modeling."""

    name: str
    sv_type: str
    is_rand: bool
    default_value: str | None = None
    comment: str = ""
    direction: Direction | None = None
    is_enum: bool = False

    @property
    def uvm_field_macro(self) -> str:
        """Returns the appropriate UVM field macro string based on the variable type."""
        if self.is_enum:
            return f"`uvm_field_enum({self.sv_type}, {self.name}, UVM_ALL_ON)"
        elif self.sv_type == "string":
            return f"`uvm_field_string({self.name}, UVM_ALL_ON)"
        elif self.sv_type.startswith("uvm_"):  # Simple heuristic for objects
            return f"`uvm_field_object({self.name}, UVM_ALL_ON)"
        else:
            # logic, bit, integer, arrays of logic all fall back to int safely
            return f"`uvm_field_int({self.name}, UVM_ALL_ON)"


@dataclass
class SvConstraint:
    """Representation of a SystemVerilog constraint block."""

    name: str
    body: list[str]  # Lines of code inside the constraint block


@dataclass
class TransactionModel:
    """Data model representing a UVM transaction, which will be used to generate the corresponding SystemVerilog class."""

    class_name: str
    variables: list[SvVariable]
    constraints: list[SvConstraint]
    macros: list[str]  # Napr. `uvm_object_utils_begin` polia
