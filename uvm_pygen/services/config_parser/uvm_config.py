"""UVM Configuration Model."""

from pathlib import Path

import yaml

from uvm_pygen.models.config_schema.uvm_dataclass import Component, Sequence, Test
from uvm_pygen.services.config_parser.dut_config import DUTConfiguration


class UVMConfiguration:
    """UVM Configuration - Verification Environment"""

    def __init__(self, config_path: str, dut_config: DUTConfiguration) -> None:
        self.config_path = Path(config_path)
        self.dut_config = dut_config  # Reference to DUT config
        self._raw_config: dict = {}
        self._load()
        self._parse()

    def _load(self):
        """Load YAML file."""
        with open(self.config_path) as f:
            self._raw_config = yaml.safe_load(f)

    def _parse(self):
        """Parse configuration"""
        # Verification info
        verif = self._raw_config["verification"]
        self.project_name = verif["project_name"]
        self.testbench_name = verif["testbench_name"]
        self.uvm_version = verif["uvm_version"]

        # Environment
        env = self._raw_config.get("environment", {})
        self.env_name = env.get("name", "env")
        self.components = [Component(**c) for c in env.get("components", [])]

        # Transaction
        trans = self._raw_config.get("transactions", {})
        self.transaction_name = trans.get("name", "Transaction")
        self.auto_generate_transaction = trans.get("auto_generate_from_dut", False)
        self.field_overrides = trans.get("field_overrides", [])

        # Sequences
        self.sequences = [Sequence(**s) for s in self._raw_config.get("sequences", [])]

        # Coverage
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
