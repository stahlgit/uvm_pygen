"""Module for the reference model generation unit."""

from dataclasses import dataclass, field
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel


@dataclass
class ReferenceModelUnit(GenerationUnit):
    """Generates a reference model class based on the model."""

    key: str = "reference_model"
    deps: list[str] = field(default_factory=lambda: ["transaction", "interface"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="components/reference_model.sv.j2", suffix="_reference_model.sv", subdir="env")
    ]

    def _prefix(self, model: EnvModel) -> str:
        return model.dut_instance_name

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        return {
            "refmodel_name": f"{model.dut_instance_name}_reference_model",
            "trans_type": reg.get_context("trans_type", self.key),
            "trans": model.transaction,
        }

    def _post_run(self, registry, model, written):
        registry.register(self.key, reference_model=f"{model.dut_instance_name}_reference_model")
        # we do not assign the reference model as a source file, as it is part of env package and not a separate component
        # pkg_filename = f"{model.dut_instance_name}_reference_model.sv"
        # if pkg_filename in written:
        #    self._register_src_file(registry, written[pkg_filename], model.testbench_name)
