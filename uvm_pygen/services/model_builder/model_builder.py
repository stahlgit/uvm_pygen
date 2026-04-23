"""Service to build Logic Models from Raw Configurations."""

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction, ReferenceModelStrategy
from uvm_pygen.models.config_schema.dut_dataclass import Port
from uvm_pygen.models.config_schema.uvm_dataclass import Connection, ReferenceModelConfig
from uvm_pygen.models.logic_schema.env_model import AgentModel, EnvModel, InterfaceModel
from uvm_pygen.models.logic_schema.reference_model import ReferenceModelModel, ResolvedConnection
from uvm_pygen.models.logic_schema.scoreboard_model import ScoreboardExport, ScoreboardModel
from uvm_pygen.models.logic_schema.sequence_model import SequenceModel
from uvm_pygen.models.logic_schema.transaction_model import SvVariable, TransactionModel
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

        ### INTERFACE
        interface_models = self._build_interface_models()

        ### TRANSACTIONS
        transactions = self._build_transactions(interface_models)

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
                transaction=agent.transaction,
            )
            agents.append(agent_model)

        reference_model = self._build_reference_model(agents, transactions)

        active_count = len([a for a in agents if a.mode == AgentMode.ACTIVE])
        if active_count > 1 and reference_model and reference_model.strategy == ReferenceModelStrategy.AP_SUBSCRIBER:
            raise NotImplementedError("Multiple active agents are not yet supported in generated code.")
        if active_count != 2 and reference_model and reference_model.strategy == ReferenceModelStrategy.DUAL_AGENT:
            raise ValueError("dual_agent strategy requires exactly 2 active agents.")

        return EnvModel(
            project_name=self.loader.uvm.project_name,
            testbench_name=self.loader.uvm.testbench_name,
            agents=agents,
            interfaces=list(interface_models.values()),
            scoreboard=self._build_scoreboard_model(
                agents,
                resolved_connections=reference_model.connections if reference_model else None,
            ),
            transactions=transactions,
            sequences=self._build_sequences(),
            parameters=self.loader.dut.parameters,
            enums=self.loader.dut.enums,
            dut_instance_name=self.loader.dut.dut_info.name,
            dut_entity_name=self.loader.dut.dut_info.entity_name,
            reference_model=reference_model,
        )

    def _build_variables_from_ports(self, ports: list, field_overrides: list) -> list[SvVariable]:
        """Build SvVariable list from interface ports, applying field overrides."""
        # Build override lookup by port name (lowercase for case-insensitive match)
        override_map = {fo.name.lower(): fo for fo in field_overrides}

        variables = []
        for port in ports:
            if port.is_clock or port.is_reset:
                continue  # clock/reset handled separately in interface, not in transaction

            sv_type = self._get_sv_type_from_port(port)
            override = override_map.get(port.name.lower())

            is_rand = override.randomize if override else True
            default_val = str(override.default) if override and override.default is not None else None

            variables.append(
                SvVariable(
                    name=port.name.lower(),
                    sv_type=sv_type,
                    is_rand=is_rand,
                    default_value=default_val,
                    comment=port.description,
                    direction=Direction(port.direction) if port.direction else None,
                    is_enum=bool(port.enum_def),
                )
            )

        return variables

    def _build_transactions(self, interface_models: dict[str, InterfaceModel]) -> list[TransactionModel]:
        """Build transaction models from UVM config, resolving port types from interfaces."""
        trans_to_iface: dict[str, str] = {}
        for agent_cfg in self.loader.uvm.agents:
            if agent_cfg.transaction:
                trans_to_iface[agent_cfg.transaction] = agent_cfg.interface

        # Fallback interface — first agent's interface, for single-transaction configs
        fallback_iface_name: str | None = self.loader.uvm.agents[0].interface if self.loader.uvm.agents else None

        transaction_models = []

        for trans_cfg in self.loader.uvm.transactions:
            iface_name = trans_to_iface.get(trans_cfg.name, fallback_iface_name)

            if iface_name is None:
                logger.warning(f"Transaction '{trans_cfg.name}' has no interface — generating empty transaction.")
                ports = []
            else:
                iface_model = interface_models.get(iface_name)
                if iface_model is None:
                    logger.warning(
                        f"Transaction '{trans_cfg.name}' references unknown interface '{iface_name}' — generating empty transaction."
                    )
                    ports = []
                else:
                    ports = iface_model.ports

            variables = self._build_variables_from_ports(ports, trans_cfg.field_overrides)
            transaction_models.append(
                TransactionModel(
                    class_name=trans_cfg.name,
                    base_class=trans_cfg.base_class,
                    variables=variables,
                )
            )
        return transaction_models

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

    def _build_scoreboard_model(
        self, agents: list[AgentModel], resolved_connections: list[ResolvedConnection]
    ) -> ScoreboardModel:
        """Build scoreboard model with typed exports.

        Export derivation strategy (two sources, merged):

        1. **From resolved connections** (reference model wiring) — any connection
        whose ``to_component`` is "scoreboard" contributes an export.
        Role is inferred from the port name suffix ("expected" / "actual").
        Transaction type comes directly from the connection.

        2. **From monitor agents** (fallback / supplement) — every agent with a
        MONITOR that was NOT already covered by a connection contributes an
        "actual" export, using the agent's declared transaction type.
        """
        sb_exports: list[ScoreboardExport] = []
        covered_agents: set[str] = set()  # agent names already handled via connections

        # --- Source 1: explicit connections targeting the scoreboard ---
        if resolved_connections:
            for conn in resolved_connections:
                if conn.to_component != "scoreboard":
                    continue

                # Infer role from port name, e.g. "write_expected_export" → "expected"
                port = conn.to_port  # e.g. "write_expected_export"
                if "expected" in port:
                    role = "expected"
                elif "actual" in port:
                    role = "actual"
                else:
                    role = "actual"  # safe default
                    logger.warning(f"Cannot infer scoreboard export role from port '{port}' — defaulting to 'actual'.")

                # Transaction type must come from the connection (it's typed per-wire)
                if not conn.transaction:
                    logger.warning(f"Connection to scoreboard port '{port}' has no transaction type — skipping.")
                    continue

                # imp_suffix and port_name are derived from the port name
                # e.g. port "write_expected_export" → suffix "_write_expected"
                imp_suffix = "_" + port.removesuffix("_export")

                sb_exports.append(
                    ScoreboardExport(
                        port_name=port,
                        imp_suffix=imp_suffix,
                        transaction_type=conn.transaction,
                        role=role,
                        agent_name=conn.from_component,
                    )
                )
                covered_agents.add(conn.from_component)

        # --- Source 2: monitor agents not already covered ---
        # Skip entirely if the user wired up scoreboard connections explicitly (source 1 produced exports).
        # Fallback is only for configs that have no explicit scoreboard connections at all.
        if sb_exports:
            return ScoreboardModel(
                name=f"{self.loader.dut.dut_info.name}_scoreboard",
                exports=sb_exports,
                has_predictor=True,
            )

        for agent in agents:
            if not agent.has(ComponentType.MONITOR):
                continue
            if agent.name in covered_agents:
                continue

            # Resolve transaction type: prefer agent-declared, fall back to first transaction
            trans_type = agent.transaction
            if not trans_type:
                if self.loader.uvm.transactions:
                    trans_type = self.loader.uvm.transactions[0].name
                    logger.warning(
                        f"Agent '{agent.name}' has no transaction declared — "
                        f"falling back to '{trans_type}' for scoreboard export."
                    )
                else:
                    logger.warning(
                        f"Agent '{agent.name}' has no transaction and no transactions are defined — "
                        f"skipping scoreboard export."
                    )
                    continue

            port_name = f"{agent.name}_actual_export"
            imp_suffix = f"_{agent.name}_actual"

            sb_exports.append(
                ScoreboardExport(
                    port_name=port_name,
                    imp_suffix=imp_suffix,
                    transaction_type=trans_type,
                    role="actual",
                    agent_name=agent.name,
                )
            )

        return ScoreboardModel(
            name=f"{self.loader.dut.dut_info.name}_scoreboard",
            exports=sb_exports,
            has_predictor=True,
        )

    def _build_sequences(self) -> list[SequenceModel]:
        # TODO: this is outdated, but not sure if i even will need sequences
        seq_models = []
        for seq_cfg in self.loader.uvm.sequences:
            # NOTE: future support for constrains
            # sv_constraints = []
            # if seq_cfg.constraints:
            #     sv_constraints.append(SvConstraint(name=f"{seq_cfg.name}_c", body=seq_cfg.constraints))

            model = SequenceModel(
                name=seq_cfg.name,
                base_class=seq_cfg.extends if seq_cfg.extends else "uvm_sequence",
                # transaction_type=seq_cfg.transaction if seq_cfg.transaction else self.loader.uvm.transaction_name,
                # constraints=sv_constraints,
            )
            seq_models.append(model)
        return seq_models

    def _build_reference_model(
        self, agents: list[AgentModel], transactions: list[TransactionModel]
    ) -> ReferenceModelModel | None:
        """Build and validate the reference model from config."""
        rm_cfg: None | ReferenceModelConfig = self.loader.uvm.reference_model
        if rm_cfg is None:
            return None

        agent_names = {agent.name for agent in agents}
        valid_components = agent_names | {"reference_model", "scoreboard"}

        valid_transaction_names = {t.class_name for t in transactions}

        connections = self._resolve_connections(rm_cfg.connects, valid_components, valid_transaction_names)
        # TODO: are class name and transaction needed ?
        return ReferenceModelModel(
            class_name=f"{self.loader.dut.dut_info.name}_reference_model",
            strategy=rm_cfg.strategy,
            implementation=rm_cfg.implementation.type,
            dpi_function=rm_cfg.implementation.function,
            dpi_header=rm_cfg.implementation.header,
            connections=connections,
        )

    def _resolve_connections(
        self, connects: list[Connection], valid_components: set[str], valid_transaction_names: set[str]
    ) -> list[ResolvedConnection]:
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

            if from_comp not in valid_components:
                raise ValueError(
                    f"Config Error: Connection source '{from_comp}' in '{conn.from_endpoint}' "
                    f"does not exist. Valid components: {', '.join(valid_components)}"
                )
            if to_comp not in valid_components:
                raise ValueError(
                    f"Config Error: Connection destination '{to_comp}' in '{conn.to_endpoint}' "
                    f"does not exist. Valid components: {', '.join(valid_components)}"
                )

            if conn.transaction and conn.transaction in valid_transaction_names:
                transaction = conn.transaction
            else:
                # NOTE: Here we could auto detect transaction if there is
                if conn.transaction:
                    logger.warning(
                        f"Connection transaction '{conn.transaction}' is not a valid transaction name — ignoring."
                    )
                transaction = None
            resolved.append(
                ResolvedConnection(
                    from_component=from_comp,
                    from_port=from_port,
                    to_component=to_comp,
                    to_port=to_port,
                    transaction=transaction,
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
