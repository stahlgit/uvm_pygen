"""Data models for internal representation of UVM transactions."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from uvm_pygen.constants.uvm_enum import Direction
from uvm_pygen.models.utils.util_annotation import NonEmptyStr


class SvVariable(BaseModel):
    """Representation of a SystemVerilog variable for transaction modeling.

    Immutable after construction — variables are built once by ModelBuilder
    and only read by generation units and Jinja2 templates.
    """

    model_config = ConfigDict(frozen=True)

    name: NonEmptyStr
    sv_type: NonEmptyStr
    is_rand: bool
    default_value: str | None = None
    comment: str = ""
    direction: Direction | None = None
    is_enum: bool = False

    @model_validator(mode="after")
    def enum_requires_non_primitive_type(self) -> SvVariable:
        """Catch the common mistake of marking a logic/bit variable as is_enum=True."""
        primitive_types = {"logic", "bit", "integer", "int", "string", "byte"}
        if self.is_enum and self.sv_type.lower() in primitive_types:
            raise ValueError(
                f"SvVariable '{self.name}' is marked is_enum=True but sv_type "
                f"'{self.sv_type}' is a primitive. Use the enum type name instead."
            )
        return self

    @property
    def uvm_field_macro(self) -> str:
        """Return the appropriate UVM field macro string based on the variable type.

        This is a computed property, not a stored field — Pydantic will not
        include it in serialisation, which is correct.
        """
        if self.is_enum:
            return f"`uvm_field_enum({self.sv_type}, {self.name}, UVM_ALL_ON)"
        if self.sv_type == "string":
            return f"`uvm_field_string({self.name}, UVM_ALL_ON)"
        if self.sv_type.startswith("uvm_"):
            return f"`uvm_field_object({self.name}, UVM_ALL_ON)"
        # logic, bit, integer, and arrays of logic all fall back to int safely
        return f"`uvm_field_int({self.name}, UVM_ALL_ON)"


class TransactionModel(BaseModel):
    """Data model representing a UVM transaction.

    Built once by ModelBuilder from the DUT config and UVM config field
    overrides, then passed through the registry to generation units.
    All fields are immutable after construction.
    """

    model_config = ConfigDict(frozen=True)

    class_name: NonEmptyStr
    base_class: str = "uvm_sequence_item"
    variables: list[SvVariable] = Field(default_factory=list)

    # maybe in future
    # constraints: list[SvConstraint] = Field(default_factory=list)
    # macros: list[str] = Field(default_factory=list)  # e.g. `uvm_object_utils_begin` fields

    @property
    def rand_variables(self) -> list[SvVariable]:
        """Convenience: return only the randomisable variables."""
        return [v for v in self.variables if v.is_rand]

    @property
    def nonrand_variables(self) -> list[SvVariable]:
        """Convenience: return only the non-randomisable variables."""
        return [v for v in self.variables if not v.is_rand]
