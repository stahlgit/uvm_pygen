"""Model representing internal logic for UVM interface generation."""

from pydantic import BaseModel, ConfigDict, field_validator

from uvm_pygen.models.config_schema.dut_dataclass import Port
from uvm_pygen.models.utils.util_annotation import NonEmptyStr


class InterfaceModel(BaseModel):
    """Represents a SystemVerilog interface (e.g. alu_if.sv).

    Holds resolved Port objects rather than port name strings so generation
    units can inspect direction, width, and enum references directly.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: NonEmptyStr
    ports: list[Port]
    clock: Port | None = None
    reset: Port | None = None

    @field_validator("ports")
    @classmethod
    def ports_must_not_be_empty(cls, v: list[Port]) -> list[Port]:
        """Ensure the interface has at least one port (a clock-only interface is unlikely)."""
        if not v:
            raise ValueError("InterfaceModel must have at least one port")
        return v

    # @model_validator(mode="after")
    # def clock_and_reset_must_be_in_ports(self) -> InterfaceModel:
    #     """Ensure clock/reset references are actually present in the port list."""
    #     port_names = {p.name for p in self.ports}
    #     if self.clock and self.clock.name not in port_names:
    #         raise ValueError(f"InterfaceModel '{self.name}': clock port '{self.clock.name}' is not in the ports list")
    #     if self.reset and self.reset.name not in port_names:
    #         raise ValueError(f"InterfaceModel '{self.name}': reset port '{self.reset.name}' is not in the ports list")
    #     return self
