"""Concrete generation unit for transaction generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.utils.logger import logger


@dataclass
class TransactionUnit(GenerationUnit):
    """GenerationUnit for creating a transaction class based on the model's transaction definition."""

    key: str = "transaction"
    deps: list[str] = field(default_factory=lambda: ["params_pkg"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="logic/transaction.sv.j2", suffix=".sv", subdir="objects"),
        FileSpec(template="logic/object_pkg.sv.j2", suffix="_pkg.sv", subdir="objects"),
    ]

    def _prefix(self, model: EnvModel) -> str:
        return model.transaction.class_name.lower()

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        return {
            "trans": model.transaction,
            "project_name": model.project_name,
            "package_name": reg.get_context("package_name", self.key),
        }

    def _post_run(self, reg: GenerationRegistry, model: EnvModel, written: dict[str, Path]) -> None:
        trans_name = model.transaction.class_name.lower()
        trans_pkg_name = f"{trans_name}_pkg"
        pkg_filename = f"{trans_name}_pkg.sv"

        reg.register(self.key, trans_type=model.transaction.class_name, trans_pkg_name=trans_pkg_name)

        if pkg_filename not in written:
            logger.warning("TransactionUnit: pkg file was not written, cannot register src file.")
            return
        self._register_src_file(reg, written[pkg_filename], model.testbench_name)
