"""Tests generation unit."""

from dataclasses import dataclass

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry


@dataclass
class TestsUnit(GenerationUnit):
    """Generates base test, random test, and test package as one cohesive unit."""

    key: str = "tests"
    num_transactions: int = 10
    drain_time: int = 100

    FILES = [
        FileSpec("tests/base_test.sv.j2", "_base_test.sv", subdir="tests"),
        FileSpec(
            "tests/random_test.sv.j2",
            "_random_test.sv",
            subdir="tests",
            condition=lambda reg, model: bool(
                [a for a in model.agents if a.has(ComponentType.DRIVER) and a.mode == AgentMode.ACTIVE]
            ),
        ),
        FileSpec("tests/test_pkg.sv.j2", "_test_pkg.sv", subdir="tests"),
    ]

    def __post_init__(self):
        """Set default dependencies after initialization."""
        self.deps = ["env", "interface", "agents"]

    def run(self, reg: GenerationRegistry) -> None:
        """Run the tests generation unit."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        context = {
            "name": model.dut_instance_name,
            "env_name": reg.get_context("env_name", self.key),
            "env": reg.get_context("env_pkg_name", self.key),
            "if_name": reg.get_context("if_name", self.key),
            "active_agents": [a for a in model.agents if a.has(ComponentType.DRIVER) and a.mode == AgentMode.ACTIVE],
            "num_transactions": self.num_transactions,
            "drain_time": self.drain_time,
            "agents": model.agents,
            "tests": [
                f"{model.dut_instance_name}_base_test",
                f"{model.dut_instance_name}_random_test",
            ],
        }
        written = self._render_specs(self.FILES, context, reg, model, renderer, writer, prefix=model.dut_instance_name)
        reg.register(self.key)
        pkg_filename = f"{model.dut_instance_name}_test_pkg.sv"
        if pkg_filename in written:
            reg.context.setdefault("src_files", []).append(self._tcl_path(written[pkg_filename], model.testbench_name))
