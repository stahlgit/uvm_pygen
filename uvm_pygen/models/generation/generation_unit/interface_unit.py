"""Concrete generation unit for interface generation."""

from dataclasses import dataclass, field
from typing import ClassVar, override

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.services.utils.logger import logger


@dataclass
class InterfaceUnit(GenerationUnit):
    """Generation unit for creating an interface based on the model's interface definition."""

    key: str = "interface"
    deps: list[str] = field(default_factory=lambda: ["params_pkg", "transaction"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(
            template="common/interface.sv.j2",
            suffix=".sv",
            condition=lambda _reg, model: bool(model.interfaces),
        ),
    ]

    @override
    def run(self, reg: GenerationRegistry) -> None:
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.interfaces:
            logger.warning("⚠️  No interfaces defined – skipping interface generation.")
            reg.register(self.key, if_name=None, interfaces=[])
            return

        all_written = {}
        for iface in model.interfaces:
            context = {
                "if_model": iface,
                "trans": model.transaction,
                "trans_type": reg.get_context("trans_type", self.key),
                "trans_pkg_name": reg.get_context("trans_pkg_name", self.key),
                "package_name": reg.get_context("package_name", self.key),
            }
            written = self._render_specs(context, reg, model, renderer, writer, iface.name)
            all_written.update(written)

        for path in all_written.values():
            self._register_src_file(reg, path, model.testbench_name)

        reg.register(self.key, if_name=model.interfaces[0].name, interfaces=model.interfaces)
