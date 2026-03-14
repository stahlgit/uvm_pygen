"""Tests generation unit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType
from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel


@dataclass
class TestsUnit(GenerationUnit):
    """Generates base test, random test, and test package as one cohesive unit."""

    key: str = "tests"
    deps: list[str] = field(default_factory=lambda: ["env", "interface", "agents"])

    num_transactions: int = 10
    drain_time: int = 100

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="tests/base_test.sv.j2", suffix="_base_test.sv", subdir="tests"),
        FileSpec(
            template="tests/random_test.sv.j2",
            suffix="_random_test.sv",
            subdir="tests",
            condition=lambda reg, model: bool(
                [a for a in model.agents if a.has(ComponentType.DRIVER) and a.mode == AgentMode.ACTIVE]
            ),
        ),
        FileSpec(template="tests/test_pkg.sv.j2", suffix="_test_pkg.sv", subdir="tests"),
    ]

    def _prefix(self, model: EnvModel) -> str:
        return model.dut_instance_name

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        return {
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

    def _post_run(self, reg: GenerationRegistry, model: EnvModel, written: dict[str, Path]) -> None:
        reg.register(self.key)
        pkg_filename = f"{model.dut_instance_name}_test_pkg.sv"
        if pkg_filename in written:
            self._register_src_file(reg, written[pkg_filename], model.testbench_name)
