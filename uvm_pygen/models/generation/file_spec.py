"""Specification for generating a single file from a Jinja2 template."""

from collections.abc import Callable
from dataclasses import dataclass

from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel


@dataclass
class FileSpec:
    """Specification for generating a single file from a Jinja2 template.

    Fields:
        template:   Path to the Jinja2 template (relative to the template root).
        suffix:     Output filename suffix, appended to a caller-supplied prefix.
                    Use an empty string when the prefix IS the full filename.
        subdir:     Subdirectory within the output root to write the file into.
                    None → write directly into the output root.
        condition:  Optional predicate ``(registry, model) -> bool``.
                    When provided, the spec is skipped unless the predicate returns True.
                    Signature mirrors the agent pattern but generalised:
                        lambda reg, model: <any registry/model check>
    """

    template: str
    suffix: str
    subdir: str | None = None
    condition: Callable[[GenerationRegistry, EnvModel], bool] | None = None

    def should_generate(self, registry: GenerationRegistry, model: EnvModel) -> bool:
        """Return True if this spec should be generated in the current context."""
        if self.condition is None:
            return True
        return self.condition(registry, model)

    def filename(self, prefix: str = "") -> str:
        """Construct the output filename from an optional prefix and this spec's suffix."""
        return f"{prefix}{self.suffix}"
