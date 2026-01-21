"""UVM Enums for UVM-Pygen."""

from enum import StrEnum, auto

# --- Core UVM/Agent Enums ---


class AgentMode(StrEnum):
    """Defines the operational mode of a UVM agent."""

    ACTIVE = auto()  # Agent has a driver, sequencer, and monitor
    PASSIVE = auto()  # Agent has only a monitor


class ComponentType(StrEnum):
    AGENT = auto()
    DRIVER = auto()
    MONITOR = auto()
    SEQUENCER = auto()
    SCOREBOARD = auto()

    @classmethod
    def _missing_(cls, value):
        """Hook called when ComponentType('unknown_string') is called and normalizes the input.

        Purpose:
        - Allow both "agent" and "uvm_agent" to be valid inputs for ComponentType.AGENT
        """
        if isinstance(value, str):
            clean_value = value.lower().removeprefix("uvm_").upper()

            if clean_value in cls._member_map_:
                return cls[clean_value.upper()]

        return super()._missing_(value)


class Direction(StrEnum):
    """Defines the direction of a port/signal."""

    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"


class ActiveLevel(StrEnum):
    """Defines the active level of a control signal (e.g., reset)."""

    ACTIVE_HIGH = "active_high"
    ACTIVE_LOW = "active_low"
