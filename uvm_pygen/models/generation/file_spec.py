""""""
from dataclasses import dataclass
from typing import Callable

@dataclass
class FileSpec:
    """Specification for generating a file based on an AgentModel condition."""
    template: str                   # Path to the Jinja2 template
    suffix: str                     # Output filename suffix (e.g., "_driver.sv")
    check_attr: str | None = None   # The boolean attribute in AgentModel to check (e.g., "has_driver")
    
    # Optional: If you strictly need to check specific Enum values (like active==ACTIVE)
    condition: Callable[[any], bool] | None = None