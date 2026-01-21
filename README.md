# UVM_PYGEN

## Jednoduchá reprezentácia

```mermaid
graph TD
    subgraph Vstupy
    DUT_CFG[DUT Config YAML]
    UVM_CFG[UVM Config YAML]
    TEMPL[Jinja2 Templates]
    end

    subgraph Python Generator
    LOADER[Config Loader]
    MODEL[Internal EnvModel]
    RENDER[Jinja2 Renderer]

    DUT_CFG --> LOADER
    UVM_CFG --> LOADER
    LOADER --> MODEL
    MODEL --> RENDER
    TEMPL --> RENDER
    end

    subgraph Vystup
    SV_CODE[SystemVerilog UVM Files]
    end

    RENDER --> SV_CODE
```

## Viac detailne

```mermaid
flowchart
subgraph Input Files
    config_uvm
    config_dut
end

    config_uvm --> UVMConfiguration
    config_dut --> DUTConfiguration

subgraph ConfigLoader
    DUTConfiguration
    UVMConfiguration
end

ModelBuilder


main

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

