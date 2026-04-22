"""Models representing the environment structure for UVM testbench generation."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from uvm_pygen.constants.uvm_enum import AgentMode
from uvm_pygen.models.config_schema.dut_dataclass import EnumType, Parameter
from uvm_pygen.models.logic_schema.agent_model import AgentModel
from uvm_pygen.models.logic_schema.interface_model import InterfaceModel
from uvm_pygen.models.logic_schema.reference_model import ReferenceModelModel
from uvm_pygen.models.logic_schema.scoreboard_model import ScoreboardModel
from uvm_pygen.models.logic_schema.sequence_model import SequenceModel
from uvm_pygen.models.logic_schema.transaction_model import TransactionModel
from uvm_pygen.models.utils.util_annotation import NonEmptyStr


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
        transactions:       All transaction models; each agent references one by class name.
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
    transactions: list[TransactionModel] = Field(default_factory=list)

    parameters: list[Parameter] = Field(default_factory=list)
    enums: dict[str, EnumType] = Field(default_factory=dict)

    dut_instance_name: NonEmptyStr = "dut_inst"
    dut_entity_name: NonEmptyStr = "dut_entity"

    reference_model: ReferenceModelModel | None = None

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
