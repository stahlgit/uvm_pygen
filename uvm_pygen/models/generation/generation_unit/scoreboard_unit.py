"""Module for the scoreboard generation unit."""

from dataclasses import dataclass, field
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel


@dataclass
class ScoreboardUnit(GenerationUnit):
    """Generates a scoreboard class based on the model."""

    key: str = "scoreboard"
    deps: list[str] = field(default_factory=lambda: ["transaction"])

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(
            template="components/scoreboard.sv.j2",
            suffix="_scoreboard.sv",
            subdir="env",
        ),
    ]

    def _prefix(self, model: EnvModel) -> str:
        return model.dut_instance_name

    def _build_context(self, reg: GenerationRegistry, model: EnvModel) -> dict:
        sb = model.scoreboard
        trans_by_class = {t.class_name: t for t in model.transactions}

        # Use the actual-role export to determine what the check function compares
        actual_exports = [e for e in sb.exports if e.role == "actual"] if sb else []
        actual_trans_type = (
            actual_exports[0].transaction_type if actual_exports else reg.get_context("trans_type", self.key)
        )

        return {
            "scoreboard_name": f"{model.dut_instance_name}_scoreboard",
            "scoreboard": sb,
            "trans_type": actual_trans_type,
            "trans": trans_by_class.get(actual_trans_type),
        }

    def _post_run(self, reg: GenerationRegistry, model: EnvModel, written: dict) -> None:
        reg.register(self.key, scoreboard=f"{model.dut_instance_name}_scoreboard")
        # we do not assign the scoreboard as a source file, as it is part of env package and not a separate component
        # filename = f"{model.dut_instance_name}_scoreboard.sv"
        # if filename in written:
        #    self._register_src_file(reg, written[filename], model.testbench_name)
