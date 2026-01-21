"""Service to build Logic Models from Raw Configurations."""

from dataclasses import replace

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.logic_schema.env_model import AgentModel, EnvModel, InterfaceModel
from uvm_pygen.models.logic_schema.scoreboard_model import ScoreboardModel
from uvm_pygen.models.logic_schema.sequence_model import SequenceModel
from uvm_pygen.models.logic_schema.transaction_model import SvConstraint, SvVariable, TransactionModel
from uvm_pygen.services.config_parser.config_loader import ConfigLoader


class ModelBuilder:
    """Transform Raw configurations into Logic Models."""

    def __init__(self, loader: ConfigLoader):
        """Initialize with DUT and UVM configurations."""
        self.loader = loader

    def build(self) -> EnvModel:
        """Constructs the complete Environment Model."""
        print("Building Logic Models...")

        """TODO: decide if there will be multiple interfaces, or just one per run.
        If multiple, we need to map them from UVM config to DUT ports - filter ports by interface name.
        """
        ### TRANSACTION
        transaction_model = self._build_transaction_model()

        ### INTERFACE
        control_ports = self.loader.dut.get_control_ports()
        data_in_ports = self.loader.dut.get_data_input_ports()
        data_out_ports = self.loader.dut.get_data_output_ports()
        interface_ports = control_ports + data_in_ports + data_out_ports
        clk_ports = self.loader.dut.get_clock_ports()
        rst_ports = self.loader.dut.get_reset_ports()

        resolved_interface_ports = []
        for port in interface_ports:
            try:
                width_int = self.loader.dut.resolve_width(port.width)
            except ValueError:
                print(f"Warning: Could not resolve width for {port.name}, defaulting to 1")
                width_int = 1
            resolved_interface_ports.append(replace(port, width=width_int))

        # TODO: create interfaces based on how many are defined in UVM config, right now we will create only one interface
        main_interface = InterfaceModel(
            name=self.loader.uvm.interface_list[0],
            ports=resolved_interface_ports,
            clock=clk_ports[0] if clk_ports else None,
            reset=rst_ports[0] if rst_ports else None,
        )

        ### AGENTS
        agents = []
        for comp in self.loader.uvm.components:
            if ComponentType(comp.type) == ComponentType.AGENT:
                agent_model = AgentModel(
                    name=comp.name,
                    active=AgentMode(comp.mode),
                    interface_instance=main_interface,
                    has_driver="driver" in comp.subcomponents,
                    has_monitor="monitor" in comp.subcomponents,
                )
                agents.append(agent_model)

        ### SCOREBOARD
        scoreboard_model = self._build_scoreboard_model()

        ### SEQUENCES
        sequence_models = self._build_sequences()

        return EnvModel(
            agents=agents,
            interfaces=[main_interface],
            scoreboard=scoreboard_model,
            transaction=transaction_model,
            sequences=sequence_models,
        )

    def _build_transaction_model(self) -> TransactionModel:
        """Vytvorí model transakcie spojením DUT portov a UVM nastavení."""
        variables = []

        # 1. Zozbieraj porty, ktoré chceme v transakcii
        # Zvyčajne: Control + Data Inputs + Outputs (ak chceme self-checking transakciu)
        target_ports = (
            self.loader.dut.get_control_ports()
            + self.loader.dut.get_data_input_ports()
            + self.loader.dut.get_data_output_ports()
        )

        for port in target_ports:
            # A. Rozhodni o Type (Logic vector vs Enum)
            sv_type = "logic"

            if port.enum_def:
                # Ak je port prepojený na enum, použi názov enumu (napr. "operation_t")
                sv_type = port.enum_name
            else:
                # Inak vypočítaj šírku zbernice
                width = self.loader.dut.resolve_width(port.width)
                if width > 1:
                    sv_type = f"logic [{width - 1}:0]"
                else:
                    sv_type = "logic"

            # B. Rozhodni o Randomizácii (Check overrides)
            is_rand = True
            default_val = None

            # C. Vytvor premennú
            var = SvVariable(
                name=port.name.lower(),  # SV konvencia: premenné lowercase
                sv_type=sv_type,
                is_rand=is_rand,
                default_value=default_val,
                comment=port.description,
            )
            variables.append(var)

        # 2. Vytvor model
        return TransactionModel(
            class_name=self.loader.uvm.transaction_name,
            variables=variables,
            constraints=[],  # Constraints poriešime v ďalšom kroku
            macros=[v.name for v in variables],  # Pre field automation macros
        )

    def _build_scoreboard_model(self) -> ScoreboardModel:
        # Scoreboard zvyčajne potrebuje počúvať všetkých monitorov
        # Zistíme, koľko agentov má monitor
        exports = []
        for comp in self.loader.uvm.components:
            if ComponentType.MONITOR in comp.subcomponents:
                # Názov exportu zvyčajne odvodíme od názvu agenta
                exports.append(f"{comp.name}_export")

        return ScoreboardModel(
            name=f"{self.loader.dut.dut_info.name}_scoreboard",
            transaction_type=self.loader.uvm.transaction_name,
            analysis_exports=exports,
        )

    def _build_sequences(self) -> list[SequenceModel]:
        seq_models = []
        for seq_cfg in self.loader.uvm.sequences:
            # 1. Spracuj constraints
            sv_constraints = []
            if seq_cfg.constraints:
                # Jednoduchý wrapper, v budúcnosti sem môže ísť parser syntaxe
                sv_constraints.append(SvConstraint(name=f"{seq_cfg.name}_c", body=seq_cfg.constraints))

            # 2. Vytvor Model
            model = SequenceModel(
                name=seq_cfg.name,
                base_class=seq_cfg.extends if seq_cfg.extends else "uvm_sequence",
                transaction_type=seq_cfg.transaction if seq_cfg.transaction else self.loader.uvm.transaction_name,
                constraints=sv_constraints,
            )
            seq_models.append(model)
        return seq_models
