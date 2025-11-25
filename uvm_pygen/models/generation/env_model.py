"""Top-level model representing the entire UVM environment, which resolves configuration data into hierarchical structure."""
from dataclasses import dataclass, field
from typing import Any, Self

from uvm_pygen.models.generation.agent_model import AgentModel
from uvm_pygen.services.config_parser.dut_config import DUTConfiguration
from uvm_pygen.services.config_parser.uvm_config import UVMConfiguration



@dataclass
class EnvModel:
    """Top-level model representing the entire UVM environment, which resolves configuration data into hierarchical structure."""
    
    #1 Verification / Environment Info (from UVM Config)
    project_name: str
    testbench_name: str
    env_name: str
    
    #2 DUT Configuration
    dut: Any = None # To be populated with DUTConfiguration instance
    agents: list[Any] = field(default_factory=list)  # List of AgentModel instances
    sequences: list[Any] = field(default_factory=list)  # List of SequenceModel instances
    tests: list[Any] = field(default_factory=list)  # List of TestModel instances
    
    #TODO: add more fields later
    
    @classmethod
    def create_from_configs(cls, dut_config: DUTConfiguration, uvm_config: UVMConfiguration) -> Self:
        """Factory method to construct the EnvModel by resolving and integrating data from both DUT and UVM configurations."""
        # 1. Initialize the top-level model
        env_model = cls(
            project_name=uvm_config.project_name,
            testbench_name=uvm_config.testbench_name,
            env_name=uvm_config.env_name
        )
        
        # 2. Create the DUT Model
        # env_model.dut = DUTModel.create_from_config(dut_config)
        # For now, just store the config data temporarily
        env_model.dut = dut_config 

        # 3. Create Agents and their Subcomponents (Driver, Monitor, Sequencer)
        env_model.agents = [AgentModel.create_from_config(comp, dut_config) for comp in uvm_config.components]
        # This is where the core hierarchy (Env -> Agent) is built.
        # env_model.agents = [
        #     AgentModel.create_from_config(comp, dut_config) 
        #     for comp in uvm_config.components
        # ]
        
        # 4. Create Sequence Models
        # env_model.sequences = [
        #     SequenceModel.create_from_config(seq, dut_config)
        #     for seq in uvm_config.sequences
        # ]
        
        # 5. Create Test Models
        # env_model.tests = [
        #     TestModel(test=t) for t in uvm_config.tests
        # ]

        return env_model
    
    def summary(self):
        """Print a summary of the environment model."""
        print("\n" + "="*60)
        print("ENVIRONMENT MODEL SUMMARY")
        print("="*60)
        
        print(f"\nProject: {self.project_name}")
        print(f"Testbench: {self.testbench_name}")
        print(f"Environment: {self.env_name}")
        
        print(f"\nDUT: {self.dut.dut_info.name}")
        print(f"  Description: {self.dut.dut_info.description}")
        print(f"  Data Width: {self.dut.dut_info.data_width} bits")
        
        print(f"\nAgents ({len(self.agents)} total):")
        for agent in self.agents:
            status = "Active" if agent.is_active() else "Passive"
            print(f"  - Agent: {agent.name} (Mode: {agent.mode}, Status: {status})")
            if agent.driver:
                print(f"      Driver: {agent.driver.name}")
            if agent.monitor:
                print(f"      Monitor: {agent.monitor.name}")
            if agent.sequencer:
                print(f"      Sequencer: {agent.sequencer.name}")
        
        print(f"\nSequences ({len(self.sequences)} total):")
        for seq in self.sequences:
            print(f"  - Sequence: {seq.name}")
        
        print(f"\nTests ({len(self.tests)} total):")
        for test in self.tests:
            print(f"  - Test: {test.name}")
        
    def get_agent(self, agent_name: str) -> Any:
        """Retrieve an agent by name."""
        for agent in self.agents:
            if agent.name == agent_name:
                return agent
        return None

    def get_active_agents(self) -> list[Any]:
        """Retrieve all active agents."""
        return [agent for agent in self.agents if agent.is_active()]

    def get_passive_agents(self) -> list[Any]:
        """Retrieve all passive agents."""
        return [agent for agent in self.agents if not agent.is_active()]