"""Concrete generation unit for transaction generation."""

from dataclasses import dataclass

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry


@dataclass
class TransactionUnit(GenerationUnit):
    """GenerationUnit for creating a transaction class based on the model's transaction definition."""

    key: str = "transaction"

    FILES = [FileSpec("logic/transaction.sv.j2", ".sv", subdir="objects")]

    def __post_init__(self):
        """Set default dependencies after initialization."""
        self.deps = ["params_pkg"]

    def run(self, reg: GenerationRegistry) -> None:
        """Generate the transaction class."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        context = {
            "trans": model.transaction,
            "project_name": model.project_name,
            "package_name": reg.get_context("package_name", self.key),
        }
        written = self._render_specs(
            self.FILES, context, reg, model, renderer, writer, prefix=model.transaction.class_name.lower()
        )
        path = next(iter(written.values()), None)
        reg.register(self.key, path=path, trans_type=model.transaction.class_name)
