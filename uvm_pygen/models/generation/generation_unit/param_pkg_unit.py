"""Concrete generation unit for parameter packages."""

from dataclasses import dataclass, field

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry


@dataclass
class ParamsPkgUnit(GenerationUnit):
    """Generation unit for DUT parameter packages."""

    key: str = "params_pkg"
    deps: list[str] = field(default_factory=list)

    FILES = [FileSpec("common/params_pkg.sv.j2", "_params_pkg.sv")]

    def run(self, reg: GenerationRegistry) -> None:
        """Generate the parameter package."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        pkg_name = f"{model.dut_instance_name}_params_pkg"
        context = {
            "dut_name": model.dut_instance_name,
            "parameters": model.parameters,
            "enums": model.enums,
        }
        written = self._render_specs(self.FILES, context, reg, model, renderer, writer, prefix=model.dut_instance_name)
        path = next(iter(written.values()), None)
        reg.register(self.key, path=path, package_name=pkg_name)
        if path:
            reg.context.setdefault("src_files", []).append(self._tcl_path(path, model.testbench_name))
