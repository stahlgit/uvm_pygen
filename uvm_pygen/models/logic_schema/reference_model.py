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
    transaction: str | None = None

    def _sv_handle(self, component: str) -> str:
        """Map a logical component name to its SV environment handle."""
        if component == "reference_model":
            return "m_refmodel"
        if component == "scoreboard":
            return "m_scoreboard"
        return f"m_{component}"

    @property
    def from_sv(self) -> str:
        """Get the SV handle for the source component."""
        return self._sv_handle(self.from_component)

    @property
    def to_sv(self) -> str:
        """Get the SV handle for the destination component."""
        return self._sv_handle(self.to_component)


class ReferenceModelModel(BaseModel):
    """Reference model — resolved logic model for generation."""

    model_config = ConfigDict(frozen=True)

    class_name: str  # e.g. "alu_reference_model"
    transaction_type: str  # TODO: remove since transaction type is now per-connection, not global to the RM
    strategy: ReferenceModelStrategy
    implementation: ReferenceModelImplEnum
    dpi_function: str | None = None
    dpi_header: str | None = None
    connections: list[ResolvedConnection] = Field(default_factory=list)
