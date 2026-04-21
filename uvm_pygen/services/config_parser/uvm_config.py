"""UVM Configuration Model."""

from __future__ import annotations

from typing import override

from pydantic import ValidationError

from uvm_pygen.constants.config_alliases import (
    COMPONENT_ALIASES,
    ENV_BLOCK_ALIASES,
    REFERENCE_MODEL_ALIASES,
    TRANSACTION_ALIASES,
)
from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.config_schema.uvm_dataclass import Component, ReferenceModelConfig, Sequence, TransactionField
from uvm_pygen.services.config_parser.base_config import BaseConfiguration


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
        errors.extend(self._validate_components())
        errors.extend(self._validate_sequences())
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
        self.uvm_version: str = verif.get("uvm_version", "1.2")

        # Environment
        env = self._get_aliased(self._raw_config, ENV_BLOCK_ALIASES, {})
        self.env_name: str = env.get("name", "env")

        # Reference model
        rm_raw = self._get_aliased(env, REFERENCE_MODEL_ALIASES, None)
        if rm_raw is None:
            self.reference_model = None  # → NO_RM, nie ReferenceModelConfig()
        else:
            self.reference_model = ReferenceModelConfig(**rm_raw)

        # self.strategy: ReferenceModelConfig = ReferenceModelConfig(**env.get("reference_model", {}))

        self.components: list[Component] = []
        comp_raw = self._get_aliased(env, COMPONENT_ALIASES, [])
        for raw_comp in comp_raw:
            try:
                self.components.append(Component(**raw_comp))
            except ValidationError as exc:
                name = raw_comp.get("name", "<unknown>")
                raise ValueError(f"Component '{name}' validation failed in '{source}':\n{exc}") from exc

        # Transaction
        trans = self._get_aliased(self._raw_config, TRANSACTION_ALIASES, {})
        self.transaction_name: str = trans.get("name", "Transaction")
        self.auto_generate_transaction: bool = trans.get("auto_generate_from_dut", False)

        self.field_overrides: list[TransactionField] = []
        for raw_field in trans.get("field_overrides", []):
            try:
                self.field_overrides.append(TransactionField(**raw_field))
            except ValidationError as exc:
                name = raw_field.get("name", "<unknown>")
                raise ValueError(f"TransactionField '{name}' validation failed in '{source}':\n{exc}") from exc

        # Sequences
        self.sequences: list[Sequence] = []
        for raw_seq in self._raw_config.get("sequences", []):
            try:
                self.sequences.append(Sequence(**raw_seq))
            except ValidationError as exc:
                name = raw_seq.get("name", "<unknown>")
                raise ValueError(f"Sequence '{name}' validation failed in '{source}':\n{exc}") from exc

    # -------------------------------------------------------------------------
    # Private — cross-object validation helpers
    # -------------------------------------------------------------------------

    def _validate_components(self) -> list[str]:
        """Validate all components; dispatch per-type checks."""
        errors: list[str] = []
        for component in self.components:
            if ComponentType(component.type) == ComponentType.AGENT:
                errors.extend(self._validate_agent(component))
        return errors

    def _validate_agent(self, component: Component) -> list[str]:
        """Validate agent-specific rules."""
        errors: list[str] = []

        if not component.interface:
            errors.append(f"Agent '{component.name}' must have an associated interface.")
        else:
            self.interface_list.append(component.interface)

        if component.mode and AgentMode(component.mode) == AgentMode.ACTIVE:
            errors.extend(self._ensure_subcomponent_enabled(component, ComponentType.DRIVER))
            errors.extend(self._ensure_subcomponent_enabled(component, ComponentType.SEQUENCER))
        return errors

    def _ensure_subcomponent_enabled(self, parent: Component, sub_type: ComponentType) -> list[str]:
        """Return an error list if a required subcomponent is absent or disabled."""
        sub = parent.subcomponents.get(sub_type.value) or parent.subcomponents.get(sub_type.name.lower())
        if not sub or not sub.get("enabled", False):
            return [f"Active agent '{parent.name}' must have an enabled {sub_type.name.lower()} component."]
        return []

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
