"""UVM Enums for UVM-Pygen."""

from enum import StrEnum, auto

# --- Core UVM/Agent Enums ---


class AgentMode(StrEnum):
    """Defines the operational mode of a UVM agent."""

    ACTIVE = auto()  # Agent has a driver, sequencer, and monitor
    PASSIVE = auto()  # Agent has only a monitor


class ComponentType(StrEnum):
    """Defines the type of UVM component."""

    AGENT = auto()
    DRIVER = auto()
    MONITOR = auto()
    SEQUENCER = auto()
    # Add other types as needed (e.g., ENV, TEST, SCOREBOARD)


# --- Port/Signal Enums (Often used in both DUT and UVM configs) ---


class Direction(StrEnum):
    """Defines the direction of a port/signal."""

    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"


class ActiveLevel(StrEnum):
    """Defines the active level of a control signal (e.g., reset)."""

    ACTIVE_HIGH = "active_high"
    ACTIVE_LOW = "active_low"
