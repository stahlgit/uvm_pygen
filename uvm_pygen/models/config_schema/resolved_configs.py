"""Data model for resolved configuration paths."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedConfigs:
    """Return contract for ``ConfigResolver.resolve()``."""

    dut: Path | None = None
    uvm: Path | None = None
    unified: Path | None = None

    @property
    def is_unified(self) -> bool:
        """Return True if this represents a unified config."""
        return self.unified is not None

    @property
    def is_split(self) -> bool:
        """Return True if this represents a split config."""
        return self.dut is not None or self.uvm is not None