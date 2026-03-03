"""Models representing the environment structure for UVM testbench generation."""

from dataclasses import dataclass

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.config_schema.dut_dataclass import EnumType, Parameter, Port
from uvm_pygen.models.logic_schema.scoreboard_model import ScoreboardModel
from uvm_pygen.models.logic_schema.sequence_model import SequenceModel
from uvm_pygen.models.logic_schema.transaction_model import TransactionModel


@dataclass
class InterfaceModel:
    """Representing SystemVerilog interface (alu_if.sv)."""

    name: str
    ports: list[Port]  # Tu už máme skutočné objekty portov, nie len mená
    clock: Port | None
    reset: Port | None


@dataclass
class AgentModel:
    """Representing configured agent (ready for rendering)."""

    name: str
    mode: AgentMode
    interface_instance: InterfaceModel  # Odkaz na interface
    parts: set[ComponentType]

    def has(self, part: ComponentType) -> bool:
        """Check if the agent includes a specific component type."""
        return part in self.parts


@dataclass
class EnvModel:
    """Complete model for rendering."""

    project_name: str
    testbench_name: str
    agents: list[AgentModel]
    interfaces: list[InterfaceModel]
    scoreboard: ScoreboardModel | None
    sequences: list[SequenceModel]
    transaction: TransactionModel

    parameters: list[Parameter]
    enums: dict[str, EnumType]

    dut_instance_name: str = "dut_inst"
