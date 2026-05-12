"""
Project Name: uvm_pygen
File Name: coverage_unit.py
Description: Module for the coverage generation unit.
Author: Peter Stahl (xstahl01@stud.fit.vut.cz)
Date: 2026-05-11
"""

from dataclasses import dataclass, field
from typing import ClassVar

from uvm_pygen.constants.uvm_enum import ComponentType
from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit


@dataclass
class CoverageUnit(GenerationUnit):
    """Generates a coverage class based on the model."""

    key: str = "coverage"
    deps: list[str] = field(default_factory=lambda: ["transaction"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(
            template="components/coverage.sv.j2",
            suffix="_coverage.sv",
            subdir="env",
        ),
    ]

    def _prefix(self, model) -> str:
        return model.dut_instance_name

    def run(self, reg):
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)
        trans_map = reg.get_context("transactions", self.key)

        for agent in model.agents:
            if not agent.has(ComponentType.MONITOR):
                continue
            agent_trans_info = trans_map[agent.transaction]
            trans_model = next(t for t in model.transactions if t.class_name == agent.transaction)
            context = {
                "dut_name": agent.name,  # unique per agent
                "trans_type": agent_trans_info["type"],
                "trans": trans_model,  # for coverpoint stubs per field
            }
            self._render_specs(context, reg, model, renderer, writer, prefix=agent.name)
        reg.register(self.key)
