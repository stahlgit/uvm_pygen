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
        trans_by_class = {t.class_name: t for t in model.transactions}
        rm = model.reference_model

        input_trans_type: str | None = None
        output_trans_type: str | None = None
        if rm:
            for conn in rm.connections:
                if input_trans_type is None and conn.to_component == "reference_model" and conn.transaction:
                    input_trans_type = conn.transaction
                if output_trans_type is None and conn.from_component == "reference_model" and conn.transaction:
                    output_trans_type = conn.transaction

        input_trans_type = input_trans_type or reg.get_context("trans_type", self.key)
        output_trans_type = output_trans_type or input_trans_type

        return {
            "refmodel_name": f"{model.dut_instance_name}_reference_model",
            "trans_type": input_trans_type,
            "output_trans_type": output_trans_type,
            "trans": trans_by_class.get(input_trans_type),
            "output_trans": trans_by_class.get(output_trans_type),
        }

    def _post_run(self, registry, model, written):
        registry.register(self.key, reference_model=f"{model.dut_instance_name}_reference_model")
        # we do not assign the reference model as a source file, as it is part of env package and not a separate component
        # pkg_filename = f"{model.dut_instance_name}_reference_model.sv"
        # if pkg_filename in written:
        #    self._register_src_file(registry, written[pkg_filename], model.testbench_name)
