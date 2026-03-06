"""Concrete generation unit for sequence packages."""

from dataclasses import dataclass

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.generation_unit.generation_unit import GenerationUnit
from uvm_pygen.models.generation.registry import GenerationRegistry


@dataclass
class SequencesUnit(GenerationUnit):
    """Generates sequence classes and their package based on the model."""

    key: str = "sequences"

    FILES = [
        FileSpec("sequences/base_sequence.sv.j2", "base_sequence.sv", subdir="sequences"),
        FileSpec("sequences/derived_sequence.sv.j2", "direct_sequence.sv", subdir="sequences"),
        FileSpec("sequences/random_sequence.sv.j2", "random_sequence.sv", subdir="sequences"),
        FileSpec("sequences/sequence_pkg.sv.j2", "_seq_pkg.sv", subdir="sequences"),
    ]

    def __post_init__(self):
        """Set default dependencies after initialization."""
        self.deps = ["transaction", "interface"]

    def run(self, reg: GenerationRegistry) -> None:
        """Generate sequence classes and their package based on the model."""
        reg.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(reg)

        trans_type: str = reg.get_context("trans_type", self.key)
        ports = model.interfaces[0].ports if model.interfaces else []
        seq_names = ["base_sequence", "direct_sequence", "random_sequence"]

        # Each spec has its own context slice; drive them individually.
        per_file_ctx = {
            "base_sequence.sv": {"trans_type": trans_type, "ports": ports},
            "direct_sequence.sv": {
                "seq_name": "direct_sequence",
                "trans_type": trans_type,
                "body": "// User-defined body",
            },
            "random_sequence.sv": {"trans_type": trans_type},
            f"{model.dut_instance_name}_seq_pkg.sv": {
                "name": model.dut_instance_name,
                "seqs": seq_names,
            },
        }

        for spec in self.FILES:
            if not spec.should_generate(reg, model):
                continue
            filename = (
                f"{model.dut_instance_name}{spec.suffix}"
                if spec.suffix == "_seq_pkg.sv"
                else spec.suffix  # suffix is already the full filename
            )
            content = renderer.render(spec.template, per_file_ctx[filename])
            writer.write(filename, content, subdir=spec.subdir)

        reg.register(self.key, seq_pkg_name=f"{model.dut_instance_name}_seq_pkg", seq_names=seq_names)
