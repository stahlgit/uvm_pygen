"""Simulation TCL generation unit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.utils.logger import logger


@dataclass
class SimUnit(GenerationUnit):
    """Generates a single self-contained sim.tcl for QuestaSim / ModelSim."""

    key: str = "sim"
    deps: list[str] = field(default_factory=lambda: ["top"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="sim.tcl.j2", suffix="_sim.tcl"),
    ]

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        tb = model.testbench_name
        # Top is always last in compile order — appended here rather than in
        # TopUnit, which executes before env/tests in topo order.
        top_path = Path(tb) / f"{tb}_top.sv"
        src_files = reg.context.get("src_files", []) + [self._tcl_path(top_path, tb)]
        logger.debug(f"SimUnit: adding top {top_path} to src_files")
        logger.debug(f"SimUnit: src_files now {src_files}")
        return {
            "project_name": model.project_name,
            "dut_name": model.dut_instance_name,
            "top_module": f"{tb}_top",
            "default_test": f"{model.dut_instance_name}_random_test",
            "src_files": src_files,
        }
