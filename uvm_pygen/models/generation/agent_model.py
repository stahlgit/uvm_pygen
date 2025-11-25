"""Agent Model - Represents UVM Agent and its subcomponents."""

from dataclasses import dataclass, field
from typing import Any, Self

from uvm_pygen.constants.uvm_enum import AgentMode, Direction
from uvm_pygen.models.config_schema.dut_dataclass import Port, EnumType
from uvm_pygen.models.config_schema.uvm_dataclass import Component
from uvm_pygen.services.config_parser.dut_config import DUTConfiguration

@dataclass
class InterfaceModel:
    """Model representing a resolved interface with its signals. Maps Component.interface to actual DUT ports."""
    name: str
    direction: Direction | None = None
    
    # Resolved port lists
    clock_ports: list[Port] = field(default_factory=list)
    reset_ports: list[Port] = field(default_factory=list)
    control_ports: list[Port] = field(default_factory=list)
    data_ports: list[Port] = field(default_factory=list)
    all_ports: list[Port] = field(default_factory=list)

    @classmethod
    def create_from_config(cls, component: Component, dut_config: DUTConfiguration)  -> Self:
        """Factory method to resolve interface signals from DUT configuration.
        
        Args:
            component: UVM component configuration
            dut_config: DUT configuration with port definitions
            
        Returns:
            InterfaceModel with resolved ports
        """
        interface_name = component.interface or "alu_if"
        direction = Direction(component.direction.lower()) if component.direction else None
        
        if direction == Direction.OUTPUT:
            data_ports = dut_config.get_data_output_ports()
        elif direction == Direction.INPUT:
            data_ports = dut_config.get_data_input_ports()
        else:
            data_ports = (dut_config.get_data_input_ports() + dut_config.get_data_output_ports())
        
        clock_ports = [p for p in dut_config.ports if p.is_clock]
        reset_ports = [p for p in dut_config.ports if p.is_reset]
        control_ports = dut_config.get_control_ports()
        
        all_ports = clock_ports + reset_ports + control_ports + data_ports
        return cls(
            name=interface_name,
            direction=direction,
            clock_ports=clock_ports,
            reset_ports=reset_ports,
            control_ports=control_ports,
            data_ports=data_ports,
            all_ports=all_ports
        )
    
    def get_driven_ports(self) -> list[Port]:
        """Get the list of ports driven by this interface based on its direction."""
        if self.direction == Direction.OUTPUT:
            return [] # output agents don't drive any ports #TODO: am i correct ? 
        # input agent drive control and data ports
        return self.control_ports + self.data_ports
    
    def get_monitored_ports(self) -> list[Port]:
        """Get ports that should be monitored."""
        # All agents monitor relevant ports
        return self.data_ports

@dataclass
class DriverModel:
    """Model representing a UVM Driver."""
    name: str
    driven_ports: list[Port] = field(default_factory=list)
    enums: dict[str, EnumType] = field(default_factory=dict)
    
    @classmethod
    def create(cls, agent_name: str, interface: InterfaceModel, dut_config: DUTConfiguration) -> Self:
        """Factory method to create DriverModel."""
        driven_ports = interface.get_driven_ports()
        enums = {}
        for port in driven_ports:
            if port.enum_type:
                enum_obj = dut_config.get_enum(port.enum_type)
                if enum_obj:
                    enums[port.enum_type] = enum_obj
            elif port.enum:
                enums[port.enum_type] = port.enum
        return cls(
            name=f"{agent_name}_driver",
            driven_ports=driven_ports,
            enums=enums
        )

@dataclass
class MonitorModel:
    """Model representing a UVM Monitor."""
    name: str
    monitored_ports: list[Port] = field(default_factory=list)
    enums: dict[str, EnumType] = field(default_factory=dict)
    
    @classmethod
    def create(cls, agent_name: str, interface: InterfaceModel, dut_config: DUTConfiguration) -> Self:
        """Factory method to create MonitorModel."""
        monitored_ports = interface.get_monitored_ports()
        enums = {}
        for port in monitored_ports:
            if port.enum_type:
                enum_obj = dut_config.get_enum(port.enum_type)
                if enum_obj:
                    enums[port.enum_type] = enum_obj
            elif port.enum:
                enums[port.enum_type] = port.enum
        return cls(
            name=f"{agent_name}_monitor",
            monitored_ports=monitored_ports,
            enums=enums
        )

@dataclass
class SequencerModel:
    """Model representing a UVM Sequencer."""
    name: str
    transaction_type : str
    
    @classmethod
    def create(cls, agent_name: str, transaction_type: str = "AluTransaction") -> Self:
        """Factory method to create SequencerModel."""
        return cls(
            name=f"{agent_name}_sequencer", 
            transaction_type=transaction_type
        )

@dataclass
class CoverageModel:
    """Model representing coverage collection for an agent."""
    name: str
    enabled: bool = True
    coverpoints: list[str] = field(default_factory=list)
    
    #TODO: i don't know yet
    @classmethod
    def create(cls, agent_name: str, coverpoints: list[str]) -> Self:
        """Factory method to create CoverageModel."""
        return cls(
            name=f"{agent_name}_coverage",
            coverpoints=coverpoints
        )

@dataclass
class AgentModel:
    """Model representing a UVM Agent and its subcomponents. Integrates data from both DUT and UVM configurations."""
    name: str
    type: str
    mode: AgentMode
    interface: InterfaceModel
    
    # Subcomponents
    driver: DriverModel | None = None
    monitor: MonitorModel | None = None
    sequencer: SequencerModel | None = None
    coverage: CoverageModel | None = None
    
    # Configuration references
    dut_config: DUTConfiguration | None = None
    component_config: Component | None = None
    
    @classmethod
    def create_from_config(cls, component: Component, dut_config: DUTConfiguration, translation_name:str = "AluTransaction") -> Self:
        """Factory method to create AgentModel from UVM component and DUT configuration."""
        agent_name = component.name
        agent_mode = AgentMode(component.mode.lower()) if component.mode else AgentMode.PASSIVE #TODO: default mode pasive if now defined ? 
        is_active = agent_mode == AgentMode.ACTIVE
        
        # Resolve interface
        interface = InterfaceModel.create_from_config(component, dut_config)
        
        sub_components = component.subcomponents if component.subcomponents else {}
        
        # === Driver ===
        driver = None
        if is_active and sub_components.get('driver', {}).get('enabled', True):
            driver = DriverModel.create(agent_name, interface, dut_config)
        
        #=== Monitor ===
        monitor = None
        if sub_components.get('monitor', {}).get('enabled', True):
            monitor = MonitorModel.create(agent_name, interface, dut_config)
            
        #=== Sequencer ===
        sequencer = None
        if is_active and sub_components.get('sequencer', {}).get('enabled', True):
            sequencer = SequencerModel.create(agent_name, transaction_type=translation_name)
            
        #=== Coverage ===
        coverage = None
        if sub_components.get('coverage', {}).get('enabled', True):
            coverage = CoverageModel.create(agent_name, coverpoints=[])
        
        return cls(
            name=agent_name,
            type=component.type,
            mode=agent_mode,
            interface=interface,
            driver=driver,
            monitor=monitor,
            sequencer=sequencer,
            coverage=coverage,
            dut_config=dut_config,
            component_config=component
        )
    
    def is_active(self) -> bool:
        """Check if the agent is active."""
        return self.mode == AgentMode.ACTIVE
    
    def get_all_ports(self) -> list[Port]:
        """Get all ports associated with this agent's interface."""
        return self.interface.all_ports

    def get_enum_types(self) -> dict[str, EnumType]:
        """Get all enum types used by this agent."""
        enums = {}
        if self.driver:
            enums.update(self.driver.enums)
        if self.monitor:
            enums.update(self.monitor.enums)
        return enums

    def summary(self):
        """Print agent summary."""
        print(f"\n{'='*50}")
        print(f"Agent: {self.name} ({self.mode})")
        print(f"{'='*50}")
        print(f"Type: {self.type}")
        print(f"Interface: {self.interface.name} ({self.interface.direction or 'bidirectional'})")
        print(f"\nPorts ({len(self.interface.all_ports)}):")
        print(f"  - Clock: {len(self.interface.clock_ports)}")
        print(f"  - Reset: {len(self.interface.reset_ports)}")
        print(f"  - Control: {len(self.interface.control_ports)}")
        print(f"  - Data: {len(self.interface.data_ports)}")
        
        print(f"\nSubcomponents:")
        print(f"  - Driver: {'✓' if self.driver else '✗'}")
        print(f"  - Monitor: {'✓' if self.monitor else '✗'}")
        print(f"  - Sequencer: {'✓' if self.sequencer else '✗'}")
        print(f"  - Coverage: {'✓' if self.coverage else '✗'}")
        
        if self.driver:
            print(f"\nDriver drives {len(self.driver.driven_ports)} ports:")
            for port in self.driver.driven_ports:
                print(f"  - {port.name}: {port.type}[{port.width}]")
        
        if self.monitor:
            print(f"\nMonitor observes {len(self.monitor.monitored_ports)} ports:")
            for port in self.monitor.monitored_ports:
                print(f"  - {port.name}: {port.type}[{port.width}]")
        
        enums = self.get_enum_types()
        if enums:
            print(f"\nEnum types used ({len(enums)}):")
            for enum_name in enums:
                print(f"  - {enum_name}")