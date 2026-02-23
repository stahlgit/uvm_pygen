"""Service to build Logic Models from Raw Configurations."""

from dataclasses import replace

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction
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

    def summary(self, env_model: EnvModel) -> None:
        """Prints a summary of the constructed Environment Model."""
        print("\n" + "=" * 70)
        print("INTERNAL MODEL SUMMARY")
        print("=" * 70)

        print(f"Transaction: {env_model.transaction.class_name}")
        print(f"  - Variables: {[v.name for v in env_model.transaction.variables]}")

        print(f"\nInterface: {env_model.interfaces[0].name}")
        print(f"  - Ports: {len(env_model.interfaces[0].ports)}")

        print(f"\nAgents: {len(env_model.agents)}")
        for agent in env_model.agents:
            print(f"  - {agent.name} ({agent.active})")

        if env_model.scoreboard:
            print(f"\nScoreboard: {env_model.scoreboard.name}")
            print(f"  - Exports: {env_model.scoreboard.analysis_exports}")

        print(f"\nSequences: {len(env_model.sequences)}")
        for seq in env_model.sequences:
            print(f"  - {seq.name} (Base: {seq.base_class})")

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
            resolved_interface_ports.append(
                replace(port, width=self._get_range_from_port(port))
            )  # Convert to SV range string

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
            project_name=self.loader.uvm.project_name,  # TODO: this here or higher ? nothing is higher right now
            testbench_name=self.loader.uvm.testbench_name,
            agents=agents,
            interfaces=[main_interface],
            scoreboard=scoreboard_model,
            transaction=transaction_model,
            sequences=sequence_models,
            parameters=self.loader.dut.parameters,
            enums=self.loader.dut.enums,
            dut_instance_name=self.loader.dut.dut_info.name,
        )

    def _build_transaction_model(self) -> TransactionModel:
        """Vytvorí model transakcie spojením DUT portov a UVM nastavení."""
        variables = []

        target_ports = (
            self.loader.dut.get_control_ports()
            + self.loader.dut.get_data_input_ports()
            + self.loader.dut.get_data_output_ports()
        )

        for port in target_ports:
            # A. Rozhodni o Type (Logic vector vs Enum)
            sv_type = self._get_sv_type_from_port(port)

            # B. Rozhodni o Randomizácii (Check overrides)
            is_rand = True
            default_val = None

            var = SvVariable(
                name=port.name.lower(),  # SV convention : lower
                sv_type=sv_type,
                is_rand=is_rand,
                default_value=default_val,
                comment=port.description,
                direction=Direction(port.direction) if port.direction else None,
            )
            variables.append(var)

        return TransactionModel(
            class_name=self.loader.uvm.transaction_name,
            variables=variables,
            constraints=[],
            macros=[v.name for v in variables],  # for field automation macros
        )

    def _build_scoreboard_model(self) -> ScoreboardModel:
        # Scoreboard zvyčajne potrebuje počúvať všetkých monitorov
        # Zistíme, koľko agentov má monitor
        exports = []
        for comp in self.loader.uvm.components:
            if ComponentType.MONITOR in comp.subcomponents:
                exports.append(f"{comp.name}_export")

        return ScoreboardModel(
            name=f"{self.loader.dut.dut_info.name}_scoreboard",
            transaction_type=self.loader.uvm.transaction_name,
            analysis_exports=exports,
        )

    def _build_sequences(self) -> list[SequenceModel]:
        seq_models = []
        for seq_cfg in self.loader.uvm.sequences:
            sv_constraints = []
            if seq_cfg.constraints:
                # Jednoduchý wrapper, v budúcnosti sem môže ísť parser syntaxe
                sv_constraints.append(SvConstraint(name=f"{seq_cfg.name}_c", body=seq_cfg.constraints))

            model = SequenceModel(
                name=seq_cfg.name,
                base_class=seq_cfg.extends if seq_cfg.extends else "uvm_sequence",
                transaction_type=seq_cfg.transaction if seq_cfg.transaction else self.loader.uvm.transaction_name,
                constraints=sv_constraints,
            )
            seq_models.append(model)
        return seq_models

    def _get_sv_type_from_port(self, port) -> str:
        """Convert a DUT port definition into a SystemVerilog type string."""
        if port.enum_def:
            return port.enum_name

        width = port.width
        if isinstance(width, int):
            if width == 1:
                return "logic"
            else:
                return f"logic [{width - 1}:0]"
        # If it's already a range like "(3:0)" or "(DATA_WIDTH-1:0)", convert brackets
        elif ":" in width:
            # Replace parentheses with brackets for SV style
            range_str = width.replace("(", "[").replace(")", "]")
            return f"logic {range_str}"
        else:
            # Assume it's a parameter name (e.g., "DATA_WIDTH")
            return f"logic [{width}-1:0]"

    def _get_range_from_port(self, port) -> str:
        """Return the SV range string (e.g., '[3:0]' or '[DATA_WIDTH-1:0]') or empty string for 1-bit."""
        width = port.width
        if isinstance(width, int):
            if width == 1:
                return ""
            else:
                return f"[{width - 1}:0]"
        elif ":" in width:
            # Convert (msb:lsb) to [msb:lsb]
            return width.replace("(", "[").replace(")", "]")
        else:
            return f"[{width}-1:0]"
