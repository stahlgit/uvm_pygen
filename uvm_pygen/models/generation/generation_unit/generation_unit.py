"""GenerationUnit - declarative building block for the generation pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.generation.file_manager import FileManager
from uvm_pygen.services.generation.renderer import TemplateRenderer


@dataclass
class GenerationUnit(ABC):
    """Base class for a single, self-describing generation step.

    Subclasses declare:
        key   - unique identifier used as the registry key for this unit's output.
        deps  - list of registry keys (files *or* context) that must exist before run().

    The orchestrator (Generator) resolves execution order via topological sort over deps.
    """

    key: str
    deps: list[str] = field(default_factory=list)

    @abstractmethod
    def run(self, registry: GenerationRegistry):
        """Execute this generation step.

        Implementations should:
            1. Call registry.assert_deps(self.deps, self.key) at entry.
            2. Read whatever they need via registry.get_ctx / get_file.
            3. Render + write files.
            4. Register outputs back into the registry.
        """

    def _render_specs(
        self,
        specs: list[FileSpec],
        context: dict,
        registry: GenerationRegistry,
        model: EnvModel,
        renderer: TemplateRenderer,
        writer: FileManager,
        prefix: str = "",
    ) -> dict[str, Path]:
        """Iterate a list of FileSpecs, rendering and writing each applicable one.

        Skips any spec whose condition returns False for the current registry + model.

        Args:
            specs:    List of FileSpec descriptors to process.
            context:  Jinja2 template context dict.
            registry: Active GenerationRegistry (passed to condition lambdas).
            model:    EnvModel (passed to condition lambdas).
            renderer: TemplateRenderer instance.
            writer:   FileManager instance.
            prefix:   Optional filename prefix prepended to each spec's suffix.

        Returns:
            Mapping of ``filename → written Path`` for every file that was written.
            Files skipped due to condition or write conflicts are excluded.
        """
        written: dict[str, Path] = {}

        for spec in specs:
            if not spec.should_generate(registry, model):
                continue

            filename = spec.filename(prefix)
            content = renderer.render(spec.template, context)
            path = writer.write(filename, content, subdir=spec.subdir)

            if path is not None:
                written[filename] = path

        return written

    def _infra(self, registry: GenerationRegistry) -> tuple:  # "tuple[EnvModel, TemplateRenderer, FileManager]"
        """Pull the three infrastructure objects every unit needs."""
        return (
            registry.get_context("model"),
            registry.get_context("renderer"),
            registry.get_context("writer"),
        )

    def _tcl_path(self, path: Path, tb: str) -> str:
        """Convert registry Path to space separated TCL path string relative to testbench."""
        try:
            rel = path.relative_to(tb)
            return " ".join([tb] + list(rel.parts))
        except ValueError:
            return " ".join(path.parts)
