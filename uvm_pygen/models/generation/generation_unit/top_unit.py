"""Top level Unit."""

from dataclasses import dataclass

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.services.utils import logger


@dataclass
class TopUnit(GenerationUnit):
    """Generates the top-level testbench module, connecting interfaces and agents."""

    key: str = "top"

    FILES = [
        FileSpec(
            "common/top.sv.j2",
            "_top.sv",
            condition=lambda reg, model: bool(model.interfaces),
        ),
    ]

    def __post_init__(self):
        """Set default dependencies after initialization."""
        self.deps = ["interface", "agents"]

    def run(self, reg: GenerationRegistry) -> None:
        """Run the top-level generation unit."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.interfaces:
            logger.warning("⚠️ No interfaces defined – skipping top-level generation.")
            reg.register(self.key)
            return

        iface = model.interfaces[0]
        context = {
            "testbench_name": model.testbench_name,
            "dut_instance_name": model.dut_instance_name,
            "interface": iface,
            "agents": model.agents,
            "clock": iface.clock,
            "reset": iface.reset,
            "ports": iface.ports,
        }
        self._render_specs(self.FILES, context, reg, model, renderer, writer, prefix=model.testbench_name)
        reg.register(self.key)
