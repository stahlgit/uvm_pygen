```mermaid
flowchart
Config_Loader-->Schema_Checker
Schema_Checker-->Model_Builder/Resolver
Model_Builder/Resolver --> Dependency_Graph
Dependency_Graph-->|feedback|Model_Builder/Resolver
Dependency_Graph-->Template_Engine
subgraph Generator_layer
  Template_Engine-->Code_Generator
end
Code_Generator-->Output_writter

```

Generator layer = dispatcher
```
  for agent in env_model.agents:
      self._generate_file("agent.sv.j2", {"agent": agent}, f"{agent.name}_agent.sv")
```

**Env -> Agent -> (Driver, Monitor, Sequencer)**


#### PyObjects representation 

```mermaid
flowchart TD
uvm_component:config_defined


uvm_agent:template_defined --> uvm_component:config_defined
uvm_driver:template_defined--> uvm_component:config_defined
uvm_sequencer:template_defined--> uvm_component:config_defined
uvm_monitor:template_defined--> uvm_component:config_defined

```


```
class EnvModel:
    agents: List[AgentModel]

    def __init__(self, name, agents):
        self.name = name
        self.agents = [Agent(a["name"], a["type"], a.get("active", True)) for a in agents]

class Agent:
    driver: DriverModel
    monitor: MonitorModel
    sequencer: SequencerModel

    def __init__(self, name, agent_type, active):
        self.name = name
        self.type = agent_type
        self.active = active
```

EnvModel
└── AgentModel (multiple)
    ├── InterfaceModel
    ├── DriverModel (optional - active agents only)
    ├── MonitorModel
    ├── SequencerModel (optional - active agents only)
    └── CoverageModel (optional)