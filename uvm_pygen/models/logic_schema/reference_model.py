"""Model representing internal logic for UVM reference model generation."""

from pydantic import BaseModel, ConfigDict, Field

from uvm_pygen.constants.uvm_enum import ReferenceModelImplEnum, ReferenceModelStrategy


class ResolvedConnection(BaseModel):
    """Represents a single connection between reference model and an agent/scoreboard."""

    model_config = ConfigDict(frozen=True)

    from_component: str
    from_port: str
    to_component: str
    to_port: str


class ReferenceModelModel(BaseModel):
    """Reference model — resolved logic model for generation."""

    model_config = ConfigDict(frozen=True)

    class_name: str  # e.g. "alu_reference_model"
    transaction_type: str
    strategy: ReferenceModelStrategy
    implementation: ReferenceModelImplEnum
    dpi_function: str | None = None
    dpi_header: str | None = None
    connections: list[ResolvedConnection] = Field(default_factory=list)
