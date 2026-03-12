"""Concrete generation unit for interface generation."""

from dataclasses import dataclass

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.services.utils.logger import logger


@dataclass
class InterfaceUnit(GenerationUnit):
    """GenerationUnit for creating an interface based on the model's interface definition."""

    key: str = "interface"

    FILES = [FileSpec("common/interface.sv.j2", ".sv", condition=lambda reg, model: bool(model.interfaces))]

    def __post_init__(self):
        """Set default dependencies after initialization."""
        self.deps = ["params_pkg", "transaction"]

    def run(self, reg: GenerationRegistry) -> None:
        """Generate an interface based on the model's interface definition."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.interfaces:
            logger.warning("⚠️  No interfaces defined – skipping interface generation.")
            reg.register(self.key, if_name=None)
            return

        if_model = model.interfaces[0]
        context = {
            "if_model": if_model,
            "trans": model.transaction,
            "trans_type": reg.get_context("trans_type", self.key),
            "package_name": reg.get_context("package_name", self.key),
        }
        written = self._render_specs(self.FILES, context, reg, model, renderer, writer, prefix=if_model.name)
        path = next(iter(written.values()), None)
        reg.register(self.key, path=path, if_name=if_model.name)
        if path:
            reg.context.setdefault("src_files", []).append(self._tcl_path(path, model.testbench_name))
