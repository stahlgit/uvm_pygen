"""Model representing internal logic for UVM agent configuration and generation."""

from pydantic import BaseModel, ConfigDict, field_validator

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.logic_schema.interface_model import InterfaceModel
from uvm_pygen.models.utils.util_annotation import NonEmptyStr


class AgentModel(BaseModel):
    """Represents a configured UVM agent, ready for rendering.

    ``parts`` declares which sub-components (driver, sequencer, monitor) this
    agent contains.  Use ``has()`` in FileSpec conditions and Jinja2 templates
    to guard per-component file generation.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: NonEmptyStr
    mode: AgentMode
    interface_instance: InterfaceModel
    parts: frozenset[ComponentType]  # frozenset: immutable, hashable, correct for a set of flags

    @field_validator("name")
    @classmethod
    def name_must_be_nonempty(cls, v: str) -> str:
        """Ensure agent name is not empty."""
        if not v.strip():
            raise ValueError("AgentModel.name must not be empty")
        return v

    @field_validator("parts", mode="before")
    @classmethod
    def coerce_parts_to_frozenset(cls, v) -> frozenset:
        """Accept set, list, or frozenset from ModelBuilder."""
        return frozenset(v)

    def has(self, part: ComponentType) -> bool:
        """Return True if this agent includes the given component type."""
        return part in self.parts
