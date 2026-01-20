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

```mermaid
classDiagram
    %% Generovane z config_dut.yaml
    class alu_transaction {
        rand operation_t op
        rand movi_t movi
        rand logic[7:0] reg_a
        constraint c_op
    }

    %% Generovane z config_uvm.yaml (Agents)
    class alu_driver {
        virtual alu_if vif
        run_phase() %% Tu chyba logika v YAML
    }

    class alu_monitor {
        virtual alu_if vif
        analysis_port ap
        run_phase() %% Tu chyba logika v YAML
    }

    class alu_agent {
        alu_driver drv
        alu_monitor mon
        uvm_sequencer sqr
    }

    %% Generovane z config_uvm.yaml (Env)
    class alu_env {
        alu_agent agent_input
        alu_agent agent_output
        alu_scoreboard scb
        connect_phase()
    }

    class alu_scoreboard {
        uvm_tlm_analysis_fifo input_fifo
        uvm_tlm_analysis_fifo output_fifo
        run_phase() %% Porovnavacia logika
    }

    alu_agent *-- alu_driver
    alu_agent *-- alu_monitor
    alu_env *-- alu_agent
    alu_env *-- alu_scoreboard
    alu_transaction <.. alu_driver : uses
    alu_monitor ..> alu_scoreboard : sends transaction
```

```mermaid

graph TD
    subgraph Vstup
    DUT[DUT Config]
    UVM[UVM Config]
    end

    subgraph ModelBuilder
    Logic[Logika: Type Resolution & Merging]
    end

    subgraph Internal Models
    TR_MODEL[Transaction Model]
    IF_MODEL[Interface Model]
    ENV_MODEL[Env/Agent Model]
    end

    DUT --> Logic
    UVM --> Logic
    Logic --> TR_MODEL
    Logic --> IF_MODEL
    Logic --> ENV_MODEL

    style TR_MODEL fill:#f9f,stroke:#333,stroke-width:2px
```
