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

    INPUT = auto()
    OUTPUT = auto()
    INOUT = auto()


class ActiveLevel(StrEnum):
    """Defines the active level of a control signal (e.g., reset)."""

    ACTIVE_HIGH = auto()
    ACTIVE_LOW = auto()


class ReferenceModelStrategy(StrEnum):
    """Defines the strategy for implementing a reference model in a UVM environment."""

    AP_SUBSCRIBER = auto()
    DPI_DRIVER = auto()
