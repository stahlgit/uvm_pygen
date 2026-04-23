"""Cache constants for UVM-Pygen."""

from enum import StrEnum, auto


class ConfigMode(StrEnum):
    """Defines the mode of configuration used in UVM-Pygen."""

    SPLIT = auto()  # Separate DUT and UVM config files
    UNIFIED = auto()  # Single config file containing both DUT and UVM sections
