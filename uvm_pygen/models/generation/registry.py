"""Generation registry for tracking file paths, content and shared context."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class RegistryKeyError(KeyError):
    """Raised when a required registry key is missing."""

    def __init__(self, key: str, requested_by: str) -> None:
        """Initialize the error with the missing key and the requester."""
        self.key = key
        self.requested_by = requested_by
        super().__init__(
            f"[{requested_by}] requires '{key}' but it has not been registered yet. "
            "Check generation order / dependency declarations."
        )


@dataclass
class GenerationRegistry:
    """Central store for all artefacts produced during a generation run.

    Three namespaced buckets:
        files   - registry key  ->  Path of the written file
        content - registry key  ->  rendered SV string (useful for checksums / inline includes)
        context - registry key  ->  arbitrary shared data (trans_type, if_name, package_name …)
    """

    files: dict[str, Path] = field(default_factory=dict)
    content: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def register_file(self, key: str, path: Path) -> None:
        """Register a file path under a specific key."""
        self.files[key] = path

    def register_content(self, key: str, content: str) -> None:
        """Register rendered SV content under a specific key."""
        self.content[key] = content

    def register_context(self, key: str, value: Any) -> None:
        """Register arbitrary shared data under a specific key."""
        self.context[key] = value

    def register(self, key: str, *, path: Path | None = None, content: str | None = None, **ctx: Any) -> None:
        """Convenience method: register any combination of path / content / context keys.

        The unit key is always stamped into context as a presence sentinel so
        assert_deps() can confirm the unit ran even when its file write was
        skipped (conflict / user-file preservation).
        """
        self.register_context(key, True)  # presence sentinel
        if path is not None:
            self.register_file(key, path)
        if content is not None:
            self.register_content(key, content)
        for ctx_key, ctx_val in ctx.items():
            self.register_context(ctx_key, ctx_val)

    # ------------------------------------------------------------------
    # Lookup helpers (raise RegistryKeyError on miss)
    # ------------------------------------------------------------------

    def get_file(self, key: str, requested_by: str = "unknown") -> Path:
        """Retrieve a registered file path by key, or raise if not found."""
        try:
            return self.files[key]
        except KeyError as err:
            raise RegistryKeyError(key, requested_by) from err

    def get_content(self, key: str, requested_by: str = "unknown") -> str:
        """Retrieve registered content by key, or raise if not found."""
        try:
            return self.content[key]
        except KeyError as err:
            raise RegistryKeyError(key, requested_by) from err

    def get_context(self, key: str, requested_by: str = "unknown") -> Any:
        """Retrieve registered context value by key, or raise if not found."""
        try:
            return self.context[key]
        except KeyError as err:
            raise RegistryKeyError(key, requested_by) from err

    # ------------------------------------------------------------------
    # Dependency validation
    # ------------------------------------------------------------------

    def has_file(self, key: str) -> bool:
        """Check if a file path is registered under the given key."""
        return key in self.files

    def has_content(self, key: str) -> bool:
        """Check if content is registered under the given key."""
        return key in self.content

    def assert_deps(self, deps: list[str], requested_by: str) -> None:
        """Assert that all declared dependency keys are present (files or context)."""
        for dep in deps:
            if dep not in self.files and dep not in self.context:
                raise RegistryKeyError(dep, requested_by)
