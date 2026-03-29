"""UVM Configuration Model."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.config_schema.uvm_dataclass import Component, ReferenceModelConfig, Sequence, TransactionField


class UVMConfiguration:
    """UVM Configuration - Verification Environment.

    Pydantic models validate individual components/sequences on construction;
    this class holds cross-object consistency rules (agent sub-component
    presence, sequence parent references, transaction name coherence).
    """

    def __init__(self, config_path: str | Path) -> None:
        """Initialize UVM configuration from YAML file."""
        self.config_path = Path(config_path)
        self._raw_config: dict = {}
        self.interface_list: list[str] = []
        self._load()
        self._parse()

    @classmethod
    def from_dict(cls, raw: dict, source_label: str = "<in-memory>") -> UVMConfiguration:
        """Construct a UVMConfiguration from an already-loaded dict.

        This is used when the config comes from a unified YAML file that has
        already been read and split by ``config_resolver.split_unified_config``.

        Parameters
        ----------
        raw:
            Dict with the same structure as a UVM YAML file (``verification``,
            ``environment``, ``transactions``, ``sequences``, … keys at top level).
        source_label:
            Human-readable label used in error messages (e.g. the unified file path).
        """
        instance = cls.__new__(cls)
        instance.config_path = Path(source_label)
        instance._raw_config = raw
        instance.interface_list = []
        instance._parse()
        return instance

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

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

    def _load(self) -> None:
        """Load raw YAML into _raw_config."""
        with open(self.config_path) as f:
            self._raw_config = yaml.safe_load(f)

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
        env = self._raw_config.get("environment", {})
        self.env_name: str = env.get("name", "env")

        self.strategy: ReferenceModelConfig = ReferenceModelConfig(**env.get("reference_model", {}))

        self.components: list[Component] = []
        for raw_comp in env.get("components", []):
            try:
                self.components.append(Component(**raw_comp))
            except ValidationError as exc:
                name = raw_comp.get("name", "<unknown>")
                raise ValueError(f"Component '{name}' validation failed in '{source}':\n{exc}") from exc

        # Transaction
        trans = self._raw_config.get("transactions", {})
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
