"""Wave TCL generation unit."""

from dataclasses import dataclass, field
from typing import Any, ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.models.logic_schema.interface_model import InterfaceModel


def _signal_name(port) -> str:
    """Return the Questa signal path name — enum alias when the port has one."""
    if port.enum_name:
        return port.name.lower() + "_e"
    return port.name


def _iface_context(iface: InterfaceModel) -> dict[str, Any]:
    data_ports = [p for p in iface.ports if not p.is_clock and not p.is_reset]
    return {
        "name": iface.name,
        "instance": f"{iface.name}_inst",
        "input_ports": [
            {"name": p.name, "signal_name": _signal_name(p), "width": p.width}
            for p in data_ports
            if p.direction == "input"
        ],
        "output_ports": [
            {"name": p.name, "signal_name": _signal_name(p), "width": p.width}
            for p in data_ports
            if p.direction == "output"
        ],
    }


@dataclass
class WaveUnit(GenerationUnit):
    """Generates wave.tcl for QuestaSim / ModelSim waveform configuration."""

    key: str = "wave"
    deps: list[str] = field(default_factory=lambda: ["top"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="wave.tcl.j2", suffix="wave.tcl"),
    ]

    def _prefix(self, model: EnvModel) -> str:
        return ""

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        first_iface = model.interfaces[0] if model.interfaces else None
        clock_name = first_iface.clock.name if first_iface and first_iface.clock else "CLK"
        reset_name = first_iface.reset.name if first_iface and first_iface.reset else "RST"
        return {
            "project_name": model.project_name,
            "dut_name": model.dut_instance_name,
            "top_module": f"{model.testbench_name}_top",
            "clock_name": clock_name,
            "reset_name": reset_name,
            "interfaces": [_iface_context(iface) for iface in model.interfaces],
        }
