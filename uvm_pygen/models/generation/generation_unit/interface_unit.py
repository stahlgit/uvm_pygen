"""Concrete generation unit for interface generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
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

    def _prefix(self, model: EnvModel) -> str:
        return model.interfaces[0].name if model.interfaces else ""

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        if not model.interfaces:
            return {}
        if_model = model.interfaces[0]
        return {
            "if_model": if_model,
            "trans": model.transaction,
            "trans_type": reg.get_context("trans_type", self.key),
            "package_name": reg.get_context("package_name", self.key),
        }

    def _post_run(self, reg: GenerationRegistry, model: EnvModel, written: dict[str, Path]) -> None:
        if not model.interfaces:
            logger.warning("⚠️  No interfaces defined – skipping interface generation.")
            reg.register(self.key, if_name=None)
            return

        path = next(iter(written.values()), None)
        reg.register(self.key, path=path, if_name=model.interfaces[0].name)
        if path:
            self._register_src_file(reg, path, model.testbench_name)
