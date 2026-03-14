"""Specification for generating a single file from a Jinja2 template."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from uvm_pygen.models.generation.registry import GenerationRegistry
from uvm_pygen.models.logic_schema.env_model import EnvModel

SpecCondition = Callable[[GenerationRegistry, EnvModel], bool]


class FileSpec(BaseModel):
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

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    template: str
    suffix: str
    subdir: str | None = None
    condition: SpecCondition | None = None

    @field_validator("template")
    @classmethod
    def template_must_be_nonempty(cls, v: str) -> str:
        """Catch accidental empty template paths at declaration time."""
        if not v.strip():
            raise ValueError("FileSpec.template must not be empty")
        return v

    @field_validator("condition", mode="before")
    @classmethod
    def condition_must_be_callable(cls, v: Any) -> Any:
        """Catch non-callable conditions early rather than at render time."""
        if v is not None and not callable(v):
            raise ValueError(f"FileSpec.condition must be callable, got {type(v)}")
        return v

    def should_generate(self, registry: GenerationRegistry, model: EnvModel) -> bool:
        """Return True if this spec should be generated in the current context."""
        if self.condition is None:
            return True
        return self.condition(registry, model)

    def filename(self, prefix: str = "") -> str:
        """Construct the output filename from an optional prefix and this spec's suffix."""
        return f"{prefix}{self.suffix}"

    def with_subdir(self, subdir: str, condition: SpecCondition | None = None) -> FileSpec:
        """Return a new FileSpec identical to this one but with a different subdir.

        Optionally overrides the condition predicate too.  Used by AgentsUnit to
        stamp per-agent subdirectories onto the shared class-level FILES list
        without mutating it.

        Args:
            subdir:     New subdirectory value.
            condition:  Replacement condition.  None keeps the existing one.

        Returns:
            A fresh, frozen FileSpec instance.
        """
        return FileSpec(
            template=self.template,
            suffix=self.suffix,
            subdir=subdir,
            condition=condition if condition is not None else self.condition,
        )
