"""UVM Configuration Model."""

from pathlib import Path

import yaml

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.config_schema.uvm_dataclass import Component, Sequence, Test, TransactionField


class UVMConfiguration:
    """UVM Configuration - Verification Environment."""

    def __init__(self, config_path: str) -> None:
        """Initialize UVM configuration from YAML file."""
        self.config_path = Path(config_path)
        self._raw_config: dict = {}
        self.interface_list: list[str] = []
        self._load()
        self._parse()

    def _load(self):
        """Load YAML file."""
        with open(self.config_path) as f:
            self._raw_config = yaml.safe_load(f)

    def _parse(self):
        """Parse configuration."""
        # Verification info
        verif = self._raw_config.get("verification", {})
        self.project_name = verif.get("project_name", "uvm_project")
        self.testbench_name = verif.get("testbench_name", "tb_top")
        self.uvm_version = verif.get("uvm_version", "1.2")  # TODO: or something from config later defined

        # Environment
        env = self._raw_config.get("environment", {})
        self.env_name = env.get("name", "env")
        self.components = [Component(**c) for c in env.get("components", [])]

        # Transaction
        trans = self._raw_config.get("transactions", {})
        self.transaction_name = trans.get("name", "Transaction")
        self.auto_generate_transaction = trans.get("auto_generate_from_dut", False)
        self.field_overrides = [TransactionField(**f) for f in trans.get("field_overrides", [])]

        # Sequences
        self.sequences = [Sequence(**s) for s in self._raw_config.get("sequences", [])]

        # FOR NOW LET'S IGNORE THIS PART
        """        # Coverage
        cov = self._raw_config.get("coverage", {})
        self.coverage_enabled = cov.get("enable", True)
        self.coverage_auto_generate = cov.get("auto_generate", {})
        self.custom_coverpoints = cov.get("custom_coverpoints", [])
        self.cross_coverage = cov.get("cross_coverage", [])
        self.coverage_goals = cov.get("goals", {})

        # Tests
        self.tests = [Test(**t) for t in self._raw_config.get("tests", [])]

        # Simulation
        sim = self._raw_config.get("simulation", {})
        self.simulator = sim.get("simulator", "questa")
        self.compilation_options = sim.get("compilation", {}).get("options", [])
        self.simulation_options = sim.get("simulation_options", {})
        self.waveform_config = sim.get("waveform", {})
        """

    def validate(self) -> list[str]:
        """Validate configuration consistency.

        Returns:
            list[str]: A list of error messages.
        """
        errors = []
        self._validate_components(errors)
        self._validate_sequences(errors)

    def get_sequence(self, seq_name: str) -> Sequence | None:
        """Get sequence by name."""
        for seq in self.sequences:
            if seq.name == seq_name:
                return seq
        return None

    def get_test(self, test_name: str) -> Test | None:
        """Get test by name."""
        for test in self.tests:
            if test.name == test_name:
                return test
        return None

    def _validate_components(self, errors: list[str]) -> list[str]:
        for component in self.components:
            if ComponentType(component.type) == ComponentType.AGENT:
                errors = self._validate_agent(component, errors)
            # in future add other component type validations as needed
        return errors

    def _validate_agent(self, component: Component, errors: list[str]) -> list[str]:
        if not component.interface:
            errors.append(f"Agent '{component.name}' must have an associated interface.")

        self.interface_list.append(component.interface)  # Collect interface names

        if AgentMode(component.mode) == AgentMode.ACTIVE:
            self._ensure_subcomponent_enabled(component, ComponentType.DRIVER, errors)
            self._ensure_subcomponent_enabled(component, ComponentType.SEQUENCER, errors)
        return errors

    def _ensure_subcomponent_enabled(self, parent: Component, sub_type: ComponentType, errors: list[str]) -> None:
        """Helper to check if a specific subcomponent exists and is enabled."""
        sub = parent.subcomponents.get(sub_type)

        # Check if sub is None OR if 'enabled' is False
        if not sub or not sub.get("enabled", False):
            # Using sub_type.name or str(sub_type) makes the error message dynamic
            errors.append(f"Active agent '{parent.name}' must have an enabled {sub_type.name.lower()} component.")

    def _validate_sequences(self, errors: list[str]) -> list[str]:
        seq_names = {s.name for s in self.sequences}
        for seq in self.sequences:
            # Rule: Parent sequence must exist
            if seq.extends and seq.extends not in seq_names:
                errors.append(f"Sequence '{seq.name}' extends unknown sequence '{seq.extends}'.")

            # Rule: Transaction name consistency
            if seq.transaction and seq.transaction != self.transaction_name:
                errors.append(
                    f"Sequence '{seq.name}' uses transaction '{seq.transaction}', "
                    f"but environment defines '{self.transaction_name}'."
                )
        return errors
