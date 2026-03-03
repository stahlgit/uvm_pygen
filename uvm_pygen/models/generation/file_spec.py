from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class FileSpec:
    """Specification for generating a file based on an AgentModel condition."""

    template: str  # Path to the Jinja2 template
    suffix: str  # Output filename suffix (e.g., "_driver.sv")
    condition: Callable[[any], bool] | None = None
