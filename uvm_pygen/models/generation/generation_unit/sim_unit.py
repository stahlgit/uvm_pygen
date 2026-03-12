from dataclasses import dataclass
from pathlib import Path

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry


@dataclass
class SimUnit(GenerationUnit):
    """Generates a single self-contained sim.tcl for QuestaSim / ModelSim."""

    key: str = "sim"

    FILES = [
        FileSpec("sim.tcl.j2", "_sim.tcl"),
    ]

    def __post_init__(self):
        self.deps = ["tests", "top"]

    def run(self, reg: GenerationRegistry) -> None:
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        tb = model.testbench_name

        # Top is always last in compile order – append it here rather than in
        # TopUnit.run(), which executes before env/tests in topo order.
        top_path = Path(tb) / f"{tb}_top.sv"
        src_files = reg.context.get("src_files", []) + [self._tcl_path(top_path, tb)]

        context = {
            "project_name": model.project_name,
            "dut_name": model.dut_instance_name,
            "top_module": f"{tb}_top",
            "default_test": f"{model.dut_instance_name}_random_test",
            "src_files": src_files,
        }
        self._render_specs(self.FILES, context, reg, model, renderer, writer, prefix=tb)
        reg.register(self.key)
