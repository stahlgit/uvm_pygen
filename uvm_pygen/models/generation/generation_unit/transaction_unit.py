"""Concrete generation unit for transaction generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, override

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
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

    @override
    def run(self, reg: GenerationRegistry) -> None:
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        if not model.transactions:
            logger.warning("⚠️  No transactions defined — skipping transaction generation.")
            reg.register(self.key, trans_type=None, trans_pkg_name=None)
            return

        all_written: dict[str, Path] = {}

        for trans in model.transactions:
            context = {
                "trans": trans,
                "project_name": model.project_name,
                "package_name": reg.get_context("package_name", self.key),
                "external_class": trans.base_class.lower() + "_pkg"
                if trans.base_class != "uvm_sequence_item"
                else None,
                # NOTE: possible bug, where rendering of child transaction would be earlier then parent transaction
            }
            written = self._render_specs(context, reg, model, renderer, writer, trans.class_name.lower())
            all_written.update(written)

        # Register src files — only pkg files go into the compile list
        for filename, path in all_written.items():
            if filename.endswith("_pkg.sv"):
                self._register_src_file(reg, path, model.testbench_name)

        trans_map = {
            trans.class_name: {"type": trans.class_name, "pkg_name": f"{trans.class_name.lower()}_pkg"}
            for trans in model.transactions
        }

        reg.register(self.key, transactions=trans_map)
