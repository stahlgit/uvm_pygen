"""Service to build Logic Models from Raw Configurations."""

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction
from uvm_pygen.models.config_schema.dut_dataclass import Port
from uvm_pygen.models.config_schema.uvm_dataclass import Connection
from uvm_pygen.models.logic_schema.env_model import AgentModel, EnvModel, InterfaceModel
from uvm_pygen.models.logic_schema.reference_model import ReferenceModelModel, ResolvedConnection
from uvm_pygen.models.logic_schema.scoreboard_model import ScoreboardModel
from uvm_pygen.models.logic_schema.sequence_model import SequenceModel
from uvm_pygen.models.logic_schema.transaction_model import SvConstraint, SvVariable, TransactionModel
from uvm_pygen.services.config_parser.config_loader import ConfigLoader
from uvm_pygen.services.utils.logger import logger


class ModelBuilder:
    """Transform Raw configurations into Logic Models."""

    def __init__(self, loader: ConfigLoader):
        """Initialize with DUT and UVM configurations."""
        self.loader = loader

    def build(self) -> EnvModel:
        """Constructs the complete Environment Model."""
        logger.info("Building Logic Models...")

        """TODO: decide if there will be multiple interfaces, or just one per run.
        If multiple, we need to map them from UVM config to DUT ports - filter ports by interface name.
        """

        ### INTERFACE
        interface_models = self._build_interface_models()

        ### AGENTS
        agents = []
        for agent in self.loader.uvm.agents:
            iface_model = interface_models.get(agent.interface)
            if iface_model is None:
                # Should have been caught by uvm_config validation, but guard anyway
                raise ValueError(f"Agent '{agent.name}' references unknown interface '{agent.interface}'")
            agent_model = AgentModel(
                name=agent.name,
                mode=AgentMode(agent.mode),
                interface_instance=iface_model,
                parts=frozenset(agent.components),
            )
            agents.append(agent_model)

        return EnvModel(
            project_name=self.loader.uvm.project_name,
            testbench_name=self.loader.uvm.testbench_name,
            agents=agents,
            interfaces=list(interface_models.values()),
            ### Build scoreboard
            scoreboard=self._build_scoreboard_model(agents),
            transaction=self._build_transaction_model(),
            ### build sequences
            sequences=self._build_sequences(),
            parameters=self.loader.dut.parameters,
            enums=self.loader.dut.enums,
            dut_instance_name=self.loader.dut.dut_info.name,
            dut_entity_name=self.loader.dut.dut_info.entity_name,
            reference_model=self._build_reference_model(agents),
        )

    def _build_transaction_model(self) -> TransactionModel:
        """Vytvorí model transakcie spojením DUT portov a UVM nastavení."""
        variables = []

        target_ports = self.loader.dut.get_signal_ports()

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
                is_enum=bool(port.enum_def),
            )
            variables.append(var)

        return TransactionModel(
            class_name=self.loader.uvm.transaction_name,
            variables=variables,
            constraints=[],
            macros=[v.name for v in variables],  # for field automation macros
        )

    def _resolve_interface_ports(
        self, port_names: list[str], dut_port_map: dict[str, Port], dut_group_map: dict[str, list[str]]
    ) -> list[Port]:
        """Expand group names and resolve port name strings to Port objects.

        Resolution order per entry:
        1. Group name → expands to all ports in that group
        2. Port name  → resolves directly to that Port
        3. Unknown    → warning, skipped

        Duplicates are deduplicated while preserving order.
        Clock and reset ports are excluded — they are handled separately
        via InterfaceModel.clock / .reset.
        """
        seen: set[str] = set()
        resolved: list[Port] = []

        for entry in port_names:
            candidates: list[str] = dut_group_map.get(entry, [entry])
            for port_name in candidates:
                if port_name in seen:
                    continue
                seen.add(port_name)
                port = dut_port_map.get(port_name)
                if port is None:
                    logger.warning(f"Interface port '{port_name}' not found in DUT — skipping.")
                    continue
                # Resolve width to SV range string
                resolved.append(port.model_copy(update={"width": self._get_range_from_port(port)}))

        return resolved

    def _build_interface_models(self):
        dut_port_map: dict[str, Port] = {p.name: p for p in self.loader.dut.ports}
        dut_group_map: dict[str, list[Port]] = {}
        for port in self.loader.dut.ports:
            if port.group:
                dut_group_map.setdefault(port.group, []).append(port.name)

        clk_ports = self.loader.dut.get_clock_ports()
        rst_ports = self.loader.dut.get_reset_ports()

        interface_models: dict[str, InterfaceModel] = {}
        for iface_dc in self.loader.uvm.interfaces:
            resolved_ports = self._resolve_interface_ports(iface_dc.ports, dut_port_map, dut_group_map)
            interface_models[iface_dc.name] = InterfaceModel(
                name=iface_dc.name,
                ports=resolved_ports,
                clock=clk_ports[0] if clk_ports else None,
                reset=rst_ports[0] if rst_ports else None,
            )
        return interface_models

    def _build_scoreboard_model(self, agents: list[AgentModel]) -> ScoreboardModel:
        """Build scoreboard from agents that have a monitor."""
        exports = [f"{agent.name}_export" for agent in agents if agent.has(ComponentType.MONITOR)]
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

    def _build_reference_model(self, agents: list[AgentModel]) -> ReferenceModelModel | None:
        """Build and validate the reference model from config."""
        rm_cfg = self.loader.uvm.reference_model
        if rm_cfg is None:
            return None

        agent_names = {agent.name for agent in agents}
        valid_components = agent_names | {"reference_model", "scoreboard"}

        connections = self._resolve_connections(rm_cfg.connects, valid_components)
        # TODO: are class name and transaction needed ?
        return ReferenceModelModel(
            class_name=f"{self.loader.dut.dut_info.name}_reference_model",
            transaction_type=self.loader.uvm.transaction_name,
            strategy=rm_cfg.strategy,
            implementation=rm_cfg.implementation.type,
            dpi_function=rm_cfg.implementation.function,
            dpi_header=rm_cfg.implementation.header,
            connections=connections,
        )

    def _resolve_connections(self, connects: list[Connection], valid_components: set[str]) -> list[ResolvedConnection]:
        """Parse and validate endpoint strings into ResolvedConnection objects."""
        _PORT_ALIASES: dict[str, str] = {
            "driver.ap": "m_driver.ap",
            "monitor.ap": "m_monitor.analysis_port",
            "monitor.analysis_port": "m_monitor.analysis_port",
        }

        resolved = []
        for conn in connects:
            from_comp, from_port = self._parse_endpoint(conn.from_endpoint, valid_components, _PORT_ALIASES)
            to_comp, to_port = self._parse_endpoint(conn.to_endpoint, valid_components, _PORT_ALIASES)
            resolved.append(
                ResolvedConnection(
                    from_component=from_comp,
                    from_port=from_port,
                    to_component=to_comp,
                    to_port=to_port,
                )
            )
        return resolved

    def _parse_endpoint(
        self, endpoint: str, valid_components: set[str], port_aliases: dict[str, str]
    ) -> tuple[str, str]:
        """Split 'component.rest' and resolve port aliases.

        Returns (component_name, port_expression).
        Warns if component is unknown.
        """
        parts = endpoint.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid connection endpoint '{endpoint}': expected '<component>.<port>' format.")
        component, port_expr = parts[0], parts[1]

        if component not in valid_components:
            logger.warning(
                f"Connection endpoint '{endpoint}' references unknown component "
                f"'{component}' — known: {sorted(valid_components)}"
            )

        # Resolve alias if present, otherwise pass through as-is
        resolved_port = port_aliases.get(port_expr, port_expr)
        return component, resolved_port

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
