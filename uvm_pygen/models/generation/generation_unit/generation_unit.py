"""GenerationUnit - declarative building block for the generation pipeline."""

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from uvm_pygen.models.generation.file_spec import FileSpec
from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel
from uvm_pygen.services.generation.file_manager import FileManager
from uvm_pygen.services.generation.renderer import TemplateRenderer


@dataclass
class GenerationUnit(ABC):
    """Base class for single, self-describing generation step.

    Subclasses declare:
        key   - unique identifier used as the registry key for this unit's output.
        deps  - list of registry keys (files *or* context) that must exist before run().
        FILES - list of FileSpec descriptors that this unit renders.

    The orchestrator (Generator) resolves execution order via topological sort over deps.
    """

    key: str
    deps: list[str] = field(default_factory=list)

    FILES: ClassVar[list[FileSpec]] = []  # clear contract that units must declare their FileSpecs as a class variable

    def run(self, registry: GenerationRegistry):
        """Execute this generation step.

        Default implementation covers the standard single-pass pattern:
            1. Assert deps.
            2. Pull infra.
            3. Build a shared context via ``_build_context``.
            4. Render + write all FILES via ``_render_specs``.
            5. Delegate post-processing to ``_post_run``.
        """
        registry.assert_deps(self.deps, self.key)
        model, renderer, writer = self._infra(registry)
        context = self._build_context(registry, model)
        written = self._render_specs(context, registry, model, renderer, writer)
        self._post_run(registry, model, written)

    def _build_context(self, registry, model) -> dict:
        """Override to provide the shared template context."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement _build_context or override run()")

    def _prefix(self, model: EnvModel) -> str:
        """Return the filename prefix passed to every FileSpec.

        Default is the testbench name.  Override when a different prefix is needed
        (e.g. ``model.dut_instance_name`` or a per-agent name).
        """
        return model.testbench_name

    def _post_run(self, registry: GenerationRegistry, model: EnvModel, written: dict[str, Path]) -> None:
        """Handle post-render registration.

        Default: stamp the unit key as present in the registry.
        Override to also register context values, append src_files, etc.

        Args:
            registry: Active GenerationRegistry.
            model:   EnvModel for the current run.
            written: Mapping of ``filename → Path`` for every file written this step.
        """
        registry.register(self.key)

    def _render_specs(
        self,
        context: dict,
        registry: GenerationRegistry,
        model: EnvModel,
        renderer: TemplateRenderer,
        writer: FileManager,
        prefix: str = "",
        specs: list[FileSpec] | None = None,
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
            specs:    Optional list of FileSpecs to process; defaults to self.FILES.

        Returns:
            Mapping of ``filename → written Path`` for every file that was written.
            Files skipped due to condition or write conflicts are excluded.
        """
        resolved_specs = specs if specs is not None else self.FILES
        written: dict[str, Path] = {}

        for spec in resolved_specs:
            if not spec.should_generate(registry, model):
                continue

            filename = spec.filename(prefix)
            content = renderer.render(spec.template, context)
            path = writer.write(filename, content, subdir=spec.subdir)

            if path is not None:
                written[filename] = path

        return written

    def _infra(self, registry: GenerationRegistry) -> tuple:
        """Pull the three infrastructure objects every unit needs."""
        return (
            registry.get_context("model"),
            registry.get_context("renderer"),
            registry.get_context("writer"),
        )

    def _register_src_file(self, registry: GenerationRegistry, path: Path, tb: str) -> None:
        """Append a TCL-formatted path to the shared src_files list in the registry."""
        registry.context.setdefault("src_files", []).append(self._tcl_path(path, tb))

    def _tcl_path(self, path: Path, tb: str) -> str:
        """Convert registry Path to space separated TCL path string relative to testbench."""
        try:
            rel = path.relative_to(tb)
            return " ".join([tb] + list(rel.parts))
        except ValueError:
            return " ".join(path.parts)
