"""Models representing the environment structure for UVM testbench generation."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.config_schema.dut_dataclass import EnumType, Parameter, Port
from uvm_pygen.models.logic_schema.scoreboard_model import ScoreboardModel
from uvm_pygen.models.logic_schema.sequence_model import SequenceModel
from uvm_pygen.models.logic_schema.transaction_model import TransactionModel
from uvm_pygen.models.utils.util_annotation import NonEmptyStr


class InterfaceModel(BaseModel):
    """Represents a SystemVerilog interface (e.g. alu_if.sv).

    Holds resolved Port objects rather than port name strings so generation
    units can inspect direction, width, and enum references directly.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: NonEmptyStr
    ports: list[Port]
    clock: Port | None = None
    reset: Port | None = None

    @field_validator("ports")
    @classmethod
    def ports_must_not_be_empty(cls, v: list[Port]) -> list[Port]:
        """Ensure the interface has at least one port (a clock-only interface is unlikely)."""
        if not v:
            raise ValueError("InterfaceModel must have at least one port")
        return v

    @model_validator(mode="after")
    def clock_and_reset_must_be_in_ports(self) -> InterfaceModel:
        """Ensure clock/reset references are actually present in the port list."""
        port_names = {p.name for p in self.ports}
        if self.clock and self.clock.name not in port_names:
            raise ValueError(f"InterfaceModel '{self.name}': clock port '{self.clock.name}' is not in the ports list")
        if self.reset and self.reset.name not in port_names:
            raise ValueError(f"InterfaceModel '{self.name}': reset port '{self.reset.name}' is not in the ports list")
        return self


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


class EnvModel(BaseModel):
    """Root model passed through the generation pipeline.

    Built once by ModelBuilder and stored in the registry under the "model"
    key.  Every generation unit reads from this object — nothing writes to it
    after construction.

    Fields:
        project_name:       Top-level project identifier.
        testbench_name:     Used as a prefix for generated file/class names.
        agents:             All configured agents in dependency order.
        interfaces:         All SystemVerilog interfaces (usually one per agent).
        scoreboard:         Optional scoreboard model; None if not configured.
        sequences:          All sequences to generate.
        transaction:        The single shared transaction model.
        parameters:         DUT parameters forwarded to the params package.
        enums:              DUT enum types forwarded to the params package.
        dut_instance_name:  Instance name used in top-level binding.
        dut_entity_name:    Entity/module name of the DUT.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    project_name: NonEmptyStr
    testbench_name: NonEmptyStr
    agents: list[AgentModel] = Field(default_factory=list)
    interfaces: list[InterfaceModel] = Field(default_factory=list)
    scoreboard: ScoreboardModel | None = None
    sequences: list[SequenceModel] = Field(default_factory=list)
    transaction: TransactionModel

    parameters: list[Parameter] = Field(default_factory=list)
    enums: dict[str, EnumType] = Field(default_factory=dict)

    dut_instance_name: NonEmptyStr = "dut_inst"
    dut_entity_name: NonEmptyStr = "dut_entity"

    @model_validator(mode="after")
    def interfaces_match_agents(self) -> EnvModel:
        """Warn-level check: every agent should have a matching interface.

        This is not a hard error because an agent can theoretically be defined
        before its interface is resolved, but a mismatch almost always means
        a ModelBuilder bug and should be surfaced early.
        """
        interface_names = {i.name for i in self.interfaces}
        for agent in self.agents:
            if agent.interface_instance.name not in interface_names:
                raise ValueError(
                    f"Agent '{agent.name}' references interface "
                    f"'{agent.interface_instance.name}' which is not in EnvModel.interfaces"
                )
        return self

    # ------------------------------------------------------------------
    # Convenience properties — read-only views, not stored fields
    # ------------------------------------------------------------------

    @property
    def has_scoreboard(self) -> bool:
        """Return True if a scoreboard is configured."""
        return self.scoreboard is not None

    @property
    def active_agents(self) -> list[AgentModel]:
        """Return only active-mode agents."""
        return [a for a in self.agents if a.mode == AgentMode.ACTIVE]

    @property
    def passive_agents(self) -> list[AgentModel]:
        """Return only passive-mode agents."""
        return [a for a in self.agents if a.mode == AgentMode.PASSIVE]
