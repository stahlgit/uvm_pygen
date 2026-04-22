"""Concrete generation unit for sequence packages."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.constants.uvm_enum import AgentMode
from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.services.utils.logger import logger


@dataclass
class SequencesUnit(GenerationUnit):
    """Generates sequence classes and their package based on the model."""

    key: str = "sequences"
    deps: list[str] = field(default_factory=lambda: ["transaction", "interface"])

    num_transactions: int = 10

    FILES: ClassVar[list[FileSpec]] = [
        FileSpec(template="sequences/base_sequence.sv.j2", suffix="base_sequence.sv", subdir="sequences"),
        FileSpec(template="sequences/derived_sequence.sv.j2", suffix="direct_sequence.sv", subdir="sequences"),
        FileSpec(template="sequences/random_sequence.sv.j2", suffix="random_sequence.sv", subdir="sequences"),
        FileSpec(template="sequences/sequence_pkg.sv.j2", suffix="_seq_pkg.sv", subdir="sequences"),
    ]

    """
    The pkg spec is the only file that uses a dut-name prefix; the three
    sequence files are fixed names.  We render them by overriding run() so
    each spec can receive the right prefix independently.
    """

    _SEQ_NAMES: ClassVar[list[str]] = ["base_sequence", "direct_sequence", "random_sequence"]

    def run(self, reg: GenerationRegistry) -> None:
        """Generate sequence classes and their package."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        trans_map = reg.get_context("transactions", self.key)

        for agent in model.agents:
            if agent.mode != AgentMode.ACTIVE:
                continue

            agent_trans = trans_map.get(agent.transaction)
            if not agent_trans:
                # Fallback just in case the model references an unknown transaction
                trans_type = agent.transaction
                trans_pkg_name = f"{trans_type.lower()}_pkg"
            else:
                trans_type = agent_trans["type"]
                trans_pkg_name = agent_trans["pkg_name"]

            ports = agent.interface_instance.ports if agent.interface_instance else []

            context = {
                "trans_type": trans_type,
                "trans_pkg_name": trans_pkg_name,
                "package_name": reg.get_context("package_name", self.key),
                "ports": ports,
                "seq_name": "direct_sequence",
                "body": "// User-defined body",
                "name": model.dut_instance_name,
                "seqs": self._SEQ_NAMES,
                "num_transaction": self.num_transactions,
            }

            pkg_path: Path | None = None
            for spec in self.FILES:
                if not spec.should_generate(reg, model):
                    continue

                # Fixed-name sequence files use no prefix; the pkg uses dut_instance_name.
                prefix = model.dut_instance_name if spec.suffix == "_seq_pkg.sv" else ""
                filename = spec.filename(prefix)

                content = renderer.render(spec.template, context)
                path = writer.write(filename, content, subdir=spec.subdir)

                if path and spec.suffix == "_seq_pkg.sv":
                    pkg_path = path

            seq_pkg_name = f"{model.dut_instance_name}_seq_pkg"
            reg.register(self.key, seq_pkg_name=seq_pkg_name, seq_names=self._SEQ_NAMES)
            if not pkg_path:
                logger.warning("SequencesUnit: No package file was written, cannot register src file.")
                return

        self._register_src_file(reg, pkg_path, model.testbench_name)
