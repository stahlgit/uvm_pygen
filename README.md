# UVM_PYGEN

## Architecture Representation

```mermaid
flowchart TD
    %% Styling
    classDef logic fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef data fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef artifact fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;

    subgraph Inputs [Inputs]
        direction TB
        DUT_CFG[config_dut.yaml]:::file
        UVM_CFG[config_uvm.yaml]:::file
    end

    subgraph Phase1 [Configuration Loading]
        Loader[Config Loader]:::logic
        DUT_OBJ(DUTConfiguration):::data
        UVM_OBJ(UVMConfiguration):::data
    end

    subgraph Phase2 [Internal Representation]
        Builder[Model Builder]:::logic

        subgraph EnvModel [EnvModel Container]
            direction TB
            Ag[Agents]:::data
            If[Interface]:::data
            Tr[Transaction]:::data
            Sc[Scoreboard]:::data
            Seq[Sequences]:::data
        end
    end

    subgraph Phase3 [Code Generation]
        Generator[UVM Generator]:::logic
        Renderer[Jinja2 Renderer]:::logic
        Writer[File Writer]:::logic
        Templates[Templates .j2]:::file
    end

    subgraph Outputs [Generated TB]
        SV_FILES[SystemVerilog Files\n.sv]:::artifact
    end

    %% Connections
    DUT_CFG --> Loader
    UVM_CFG --> Loader

    Loader --> DUT_OBJ
    Loader --> UVM_OBJ

    DUT_OBJ --> Builder
    UVM_OBJ --> Builder

    Builder --> EnvModel

    EnvModel ==> Generator

    Templates -.-> Renderer
    Generator --> Renderer
    Renderer --> Writer
    Writer --> Outputs
```

## User-Friendly Regeneration: Preservation of Manual Edits
UVM_PYGEN automatically preserves manual changes made by user. No special markers or protected areas are needed.