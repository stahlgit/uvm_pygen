import re
from typing import Any
import yaml
from pathlib import Path

from uvm_pygen.models.config_schema.dut_dataclass import Constraints, DUTInfo, EnumType, EnumValue, Operation, OperationTiming, Parameter, Port


class DUTConfiguration:
    """DUT Configuration Model - Single source of truth for DUT settings."""
    
    def __init__(self, config_path: str) -> None:
        """Initialize DUT configuration from YAML file."""
        self.config_path = Path(config_path)
        self._raw_config: dict = {}
        self._load()
        self._parse()
    
    def _load(self) -> None:
        """Load YAML file."""
        with open(self.config_path) as f:
            self._raw_config = yaml.safe_load(f)
    
    def _parse(self):
        """Parse configuration into structured data."""
        dut_dict = self._raw_config["dut"]
        self.dut_info = DUTInfo(
            name=dut_dict["name"],
            description=dut_dict["description"],
            data_width=dut_dict["data_width"],
            output_width=dut_dict.get('output_width', dut_dict['data_width']),
            clock_period=dut_dict["clock_period"],
            reset_type=dut_dict["reset_type"],
            language=dut_dict["language"]
        )
        
        self.parameters = [
            Parameter(**p) for p in self._raw_config.get("parameters", [])
        ]
        self.enums = {}
        for enum_name, enum_data in self._raw_config.get('enums', {}).items():
            values = [EnumValue(**v) for v in enum_data['values']]
            self.enums[enum_name] = EnumType(
                name=enum_name,
                type=enum_data['type'],
                values=values
            )
        
        # Ports
        self.ports = [Port(**p) for p in self._raw_config.get('ports', [])]
        
        # Protocol timing
        protocol = self._raw_config.get('protocol', {})
        self.protocol_type = protocol.get('type', 'synchronous')
        self.clock_edge = protocol.get('clock_edge', 'posedge')
        self.reset_cycles = protocol.get('reset_cycles', 5)
        
        timing_dict = protocol.get('timing', {})
        self.operation_timing = {}
        for op_name, timing_data in timing_dict.items():
            self.operation_timing[op_name] = OperationTiming(**timing_data)
        
        # Operations behavior
        behavior = self._raw_config.get('behavior', {})
        self.operand_selection = behavior.get('operand_selection', {})
        self.operations = [
            Operation(**op) for op in behavior.get('operations', [])
        ]
        
        # Constraints
        constraints_dict = self._raw_config.get('constraints') or {}
        self.global_constraints = [
            Constraints(**c) for c in constraints_dict.get('global', [])
        ]
        self.corner_cases = constraints_dict.get('corner_cases', [])
        
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
        return [p for p in self.ports if p.group == 'control'] 
    
    def get_ports_by_group(self, group: str) -> list[Port]:
        """Get ports by group (e.g., 'clock', 'reset', 'data', 'control')."""
        return [p for p in self.ports if p.group == group]
    
    def get_data_input_ports(self) -> list[Port]:
        """Get all input ports."""
        return [p for p in self.ports if p.group =='input'] # TODO: make more robuts / generic

    def get_data_output_ports(self) -> list[Port]:
        """Get all output ports."""
        return [p for p in self.ports if p.group =='output'] # TODO: make more robuts / generic

    def resolve_width(self, width: Any) -> int:
        """Resolve width - can be int or parameter reference."""
        if isinstance(width, int):
            return width
        
        if not isinstance(width, str):
            raise TypeError(f"Width must be int, str, or bus string, got {type(width)}")
        
        match = re.match(r"\s*\((?P<msb>\w+)\s*:\s*(?P<lsb>\w+)\)\s*", width)
        if match:
            msb_str = match.group('msb')
            lsb_str = match.group('lsb')
            
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