"""UVM Configuration Model."""

from __future__ import annotations

from typing import override

from pydantic import ValidationError

from uvm_pygen.constants.config_alliases import (
    AGENT_ALIASES,
    ENV_BLOCK_ALIASES,
    INTERFACE_ALIASES,
    REFERENCE_MODEL_ALIASES,
    TRANSACTION_ALIASES,
)
from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.config_schema.uvm_dataclass import (
    AgentConfig,
    InterfaceDeclaration,
    ReferenceModelConfig,
    Sequence,
    TransactionConfig,
)
from uvm_pygen.services.config_parser.base_config import BaseConfiguration

UNKNOWN = "<unknown>"


class UVMConfiguration(BaseConfiguration):
    """UVM Configuration - Verification Environment.

    Pydantic models validate individual components/sequences on construction;
    this class holds cross-object consistency rules (agent sub-component
    presence, sequence parent references, transaction name coherence).
    """

    @override
    def _init_extra_state(self) -> None:
        """Initialize subclass-specific instance state before _parse() is called."""
        self.interface_list: list[str] = []

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    @override
    def validate(self) -> list[str]:
        """Validate configuration consistency.

        Returns:
            list[str]: Accumulated error messages. Empty list means valid.
        """
        errors: list[str] = []
        errors.extend(self._validate_agents())
        return errors

    def get_sequence(self, seq_name: str) -> Sequence | None:
        """Get sequence by name."""
        for seq in self.sequences:
            if seq.name == seq_name:
                return seq
        return None

    # -------------------------------------------------------------------------
    # Private — loading & parsing
    # -------------------------------------------------------------------------

    @override
    def _parse(self) -> None:
        """Parse raw config dict into Pydantic model instances.

        Each section is wrapped in its own try/except so a bad 'components'
        entry does not swallow errors from 'sequences', etc.
        """
        source = str(self.config_path)

        # Verification metadata
        verif = self._raw_config.get("verification", {})
        self.project_name: str = verif.get("project_name", "uvm_project")
        self.testbench_name: str = verif.get("testbench_name", "tb_top")

        # Environment
        env = self._get_aliased(self._raw_config, ENV_BLOCK_ALIASES, {})
        self.env_name: str = env.get("name", "env")

        # Reference model
        rm_raw = self._get_aliased(env, REFERENCE_MODEL_ALIASES, None)
        if rm_raw is None:
            self.reference_model = None  # → NO_RM, nie ReferenceModelConfig()
        else:
            self.reference_model = ReferenceModelConfig(**rm_raw)

        # Interfaces
        self.interfaces: list[InterfaceDeclaration] = []
        for raw_if in self._get_aliased(env, INTERFACE_ALIASES, []):
            try:
                self.interfaces.append(InterfaceDeclaration(**raw_if))
            except ValidationError as exc:
                name = raw_if.get("name", UNKNOWN)
                raise ValueError(f"Interface '{name}' validation failed in '{source}':\n{exc}") from exc

        # Agents
        raw_agents = self._get_aliased(env, AGENT_ALIASES, [])
        self.agents: list[AgentConfig] = []
        for raw_agent in raw_agents:
            try:
                self.agents.append(AgentConfig(**raw_agent))
            except ValidationError as exc:
                name = raw_agent.get("name", UNKNOWN)
                raise ValueError(f"Agent '{name}' validation failed in '{source}':\n{exc}") from exc

        # Transaction
        raw_trans = self._get_aliased(self._raw_config, TRANSACTION_ALIASES, {})
        self.transactions: list[TransactionConfig] = []

        for trans in raw_trans:
            try:
                self.transactions.append(TransactionConfig(**trans))
            except ValidationError as exc:
                name = raw_trans.get("name", UNKNOWN)
                raise ValueError(f"Transaction '{name}' validation failed in '{source}':\n{exc}") from exc

        # Sequences
        self.sequences: list[Sequence] = []
        for raw_seq in self._raw_config.get("sequences", []):
            try:
                self.sequences.append(Sequence(**raw_seq))
            except ValidationError as exc:
                name = raw_seq.get("name", UNKNOWN)
                raise ValueError(f"Sequence '{name}' validation failed in '{source}':\n{exc}") from exc

    # -------------------------------------------------------------------------
    # Private — cross-object validation helpers
    # -------------------------------------------------------------------------

    def _validate_agents(self) -> list[str]:
        errors = []
        iface_names = {i.name for i in self.interfaces}
        for agent in self.agents:
            if agent.interface not in iface_names:
                errors.append(
                    f"Agent '{agent.name}' references interface '{agent.interface}' "
                    f"which is not declared in env.interfaces."
                )
            if agent.mode == AgentMode.ACTIVE:
                if ComponentType.DRIVER not in agent.components:
                    errors.append(f"Active agent '{agent.name}' must include a driver.")
                if ComponentType.SEQUENCER not in agent.components:
                    errors.append(f"Active agent '{agent.name}' must include a sequencer.")
        return errors

    # def _ensure_subcomponent_enabled(self, parent: Component, sub_type: ComponentType) -> list[str]:
    #     """Return an error list if a required subcomponent is absent or disabled."""
    #     sub = parent.subcomponents.get(sub_type.value) or parent.subcomponents.get(sub_type.name.lower())
    #     if not sub or not sub.get("enabled", False):
    #         return [f"Active agent '{parent.name}' must have an enabled {sub_type.name.lower()} component."]
    #     return []

    def _validate_sequences(self) -> list[str]:
        """Validate sequence parent references and transaction name consistency."""
        errors: list[str] = []
        seq_names = {s.name for s in self.sequences}

        for seq in self.sequences:
            if seq.extends and seq.extends not in seq_names:
                errors.append(f"Sequence '{seq.name}' extends unknown sequence '{seq.extends}'.")
            if seq.transaction and seq.transaction != self.transaction_name:
                errors.append(
                    f"Sequence '{seq.name}' uses transaction '{seq.transaction}', "
                    f"but environment defines '{self.transaction_name}'."
                )
        return errors
