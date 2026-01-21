"""DUT Configuration Parser and Model."""

import re
from pathlib import Path
from typing import Any

import yaml

from uvm_pygen.models.config_schema.dut_dataclass import (
    DUTInfo,
    EnumType,
    EnumValue,
    Operation,
    Parameter,
    Port,
)


class DUTConfiguration:
    """DUT Configuration Model - Single source of truth for DUT settings."""

    ### GROUPING ALLIASES
    __CONTROL_ALIASES = {"control", "ctrl", "config", "cfg", "mode", "select", "cmd"}

    __DATA_IN_ALIASES = {"input", "data_input", "data_in", "din", "operand", "args"}

    __DATA_OUT_ALIASES = {"output", "data_output", "data_out", "dout", "result", "res"}

    def __init__(self, config_path: str) -> None:
        """Initialize DUT configuration from YAML file."""
        self.config_path = Path(config_path)
        self._raw_config: dict = {}

        # storage for detected aliases
        self.detected_control_aliases: set[str] = set()
        self.detected_data_in_aliases: set[str] = set()
        self.detected_data_out_aliases: set[str] = set()

        self._load()
        self._parse()

    def validate(self) -> list[str]:
        """Validate configuration consistency.

        Returns:
            list[str]: A list of error messages. Empty if valid.
        """
        errors = []

        # Validate and Resolve Port Enums
        for port in self.ports:
            if port.enum_name:
                if port.enum_name in self.enums:
                    # Link the object for easier access later in UVM gen
                    port.enum_def = self.enums[port.enum_name]
                else:
                    errors.append(f"Port '{port.name}' references unknown enum: '{port.enum_name}'")

        # Validate Operations against Enum
        # Assuming 'operation_t' is the standard enum name for ops (FOR NOW TODO ? CONFIGURABLE)
        operation_enum = self.get_enum("operation_t")
        if operation_enum:
            defined_ops = operation_enum.get_all_names()
            for op in self.operations:
                if op.op not in defined_ops:
                    errors.append(f"Operation logic defined for '{op.op}', but it is not in 'operation_t' enum values.")

        # Validate Groups (Moved from _resolve_group_aliases logic if you want strictness)
        try:
            self._resolve_group_aliases()
        except ValueError as e:
            errors.append(str(e))

        return errors

    def get_enum(self, enam_name: str) -> EnumType | None:
        """Get enum by name."""
        return self.enums.get(enam_name)

    def get_port(self, port_name: str) -> Port | None:
        """Get port by name."""
        for port in self.ports:
            if port.name == port_name:
                return port
        return None

    def get_operation(self, operation_name: str) -> Operation | None:
        """Get operation by name."""
        for op in self.operations:
            if op.op == operation_name:
                return op
        return None

    def get_control_ports(self) -> list[Port]:
        """Get all control ports (non-data)."""
        return [p for p in self.ports if p.group and p.group.lower() in self.__CONTROL_ALIASES]

    def get_data_input_ports(self) -> list[Port]:
        """Get all input ports."""
        return [p for p in self.ports if p.group and p.group.lower() in self.__DATA_IN_ALIASES]

    def get_data_output_ports(self) -> list[Port]:
        """Get all output ports."""
        return [p for p in self.ports if p.group and p.group.lower() in self.__DATA_OUT_ALIASES]

    def get_ports_by_group(self, group: str) -> list[Port]:
        """Get ports by group name."""
        return [p for p in self.ports if p.group and p.group.lower() == group.lower()]
    
    def get_clock_ports(self) -> list[Port]:
        """Get all clock ports."""
        return [p for p in self.ports if p.is_clock]
    
    def get_reset_ports(self) -> list[Port]:
        """Get all reset ports."""
        return [p for p in self.ports if p.is_reset]

    def resolve_width(self, width: Any) -> int:
        """Resolve width - can be int or parameter reference."""
        if isinstance(width, int):
            return width

        if not isinstance(width, str):
            raise TypeError(f"Width must be int, str, or bus string, got {type(width)}")

        # Matches (MSB:LSB) or [MSB:LSB] formats
        match = re.match(r"\s*[\[\(](?P<msb>\w+)\s*:\s*(?P<lsb>\w+)[\]\)]\s*", width)
        if match:
            msb_str = match.group("msb")
            lsb_str = match.group("lsb")

            # For simple integer bus like (3:0)
            if msb_str.isdigit() and lsb_str.isdigit():
                msb = int(msb_str)
                lsb = int(lsb_str)
                # The width is (MSB - LSB + 1). Assumes MSB >= LSB
                return msb - lsb + 1

            # If MSB/LSB are parameter references (e.g., (DATA_WIDTH-1:0)),
            # this basic resolve_width cannot handle the arithmetic.
            # For this simple implementation, we'll raise an error.
            raise ValueError(f"Arithmetic in bus width not supported: {width}")

        # Try to resolve from parameters
        for param in self.parameters:
            if param.name == width:
                return param.value

        # Try special cases
        if width == "DATA_WIDTH":
            return self.dut_info.data_width
        elif width == "OUTPUT_WIDTH":
            return self.dut_info.output_width

        raise ValueError(f"Cannot resolve width: {width}")

    def _load(self) -> None:
        """Load YAML file."""
        with open(self.config_path) as f:
            self._raw_config = yaml.safe_load(f)

    def _parse(self) -> None:
        """Parse configuration into structured data."""
        dut_dict = self._raw_config["dut"]
        self.dut_info = DUTInfo(
            name=dut_dict["name"],
            description=dut_dict["description"],
            data_width=dut_dict["data_width"],
            output_width=dut_dict.get("output_width", dut_dict["data_width"]),
            clock_period=dut_dict["clock_period"],
            reset_type=dut_dict["reset_type"],
            language=dut_dict["language"],
        )

        self.parameters = [Parameter(**p) for p in self._raw_config.get("parameters", [])]
        self.enums = {}
        for enum_name, enum_data in self._raw_config.get("enums", {}).items():
            values = [EnumValue(**v) for v in enum_data["values"]]
            self.enums[enum_name] = EnumType(name=enum_name, type=enum_data["type"], values=values)

        # Ports
        self.ports = []
        for port in self._raw_config.get("ports", []):
            if "enum_def" in port:
                port["enum_def"] = port.pop("enum_def")
            self.ports.append(Port(**port))

        # Operations behavior
        behavior = self._raw_config.get("behavior", {})
        self.operand_selection = behavior.get("operand_selection", {})
        self.operations = [Operation(**op) for op in behavior.get("operations", [])]

    def _resolve_group_aliases(self) -> None:
        """Identify which aliases are used for port groups and validate presence.

        Raises:
            ValueError: If any required group category is missing.
        """
        for port in self.ports:
            if not port.group:
                continue

            # Normalize to lower case for matching, but store original if preferred
            group_lower = port.group.lower()

            if group_lower in self.__CONTROL_ALIASES:
                self.detected_control_aliases.add(port.group)
            elif group_lower in self.__DATA_IN_ALIASES:
                self.detected_data_in_aliases.add(port.group)
            elif group_lower in self.__DATA_OUT_ALIASES:
                self.detected_data_out_aliases.add(port.group)

        # Check for missing categories
        missing_groups = []
        if not self.detected_control_aliases:
            missing_groups.append("Control (e.g., 'ctrl', 'mode')")
        if not self.detected_data_in_aliases:
            missing_groups.append("Data Input (e.g., 'din', 'operand')")
        if not self.detected_data_out_aliases:
            missing_groups.append("Data Output (e.g., 'dout', 'result')")

        if missing_groups:
            raise ValueError(
                f"Configuration Error: The following required port groups are missing from '{self.dut_info.name}': "
                f"{', '.join(missing_groups)}. "
                f"Please ensure ports are assigned valid groups in the YAML config."
            )
