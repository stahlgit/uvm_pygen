"""Top level Unit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.utils import logger


@dataclass
class TopUnit(GenerationUnit):
    """Generates the top-level testbench module, connecting interfaces and agents."""

    key: str = "top"
    deps: list[str] = field(default_factory=lambda: ["interface", "agents", "env", "tests"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(
            template="common/top.sv.j2",
            suffix="_top.sv",
            condition=lambda _reg, model: bool(model.interfaces),
        ),
    ]

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        if not model.interfaces:
            return {}
        return {
            "testbench_name": model.testbench_name,
            "dut_instance_name": model.dut_instance_name,
            "dut_entity_name": model.dut_entity_name,
            "interfaces": model.interfaces,
            "agents": model.agents,
            "clock": model.interfaces[0].clock,
            "reset": model.interfaces[0].reset,
            "all_ports": [
                (iface, port)
                for iface in model.interfaces
                for port in iface.ports
                if not port.is_clock and not port.is_reset
            ],
        }

    def _post_run(self, reg: GenerationRegistry, model: EnvModel, written: dict[str, Path]) -> None:
        if not model.interfaces:
            logger.warning("⚠️ No interfaces defined – skipping top-level generation.")
            reg.register(self.key)
            return

        reg.register(self.key)
        top_filename = f"{model.testbench_name}_top.sv"
        if top_filename in written:
            self._register_src_file(reg, written[top_filename], model.testbench_name)
