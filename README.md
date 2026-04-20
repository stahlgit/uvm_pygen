# UVM_PYGEN

## Architecture Representation

```mermaid
flowchart TD
    classDef logic    fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef data     fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef artifact fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef registry fill:#fce4ec,stroke:#c62828,stroke-width:2px;
    classDef unit     fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;
    classDef meta     fill:#ede7f6,stroke:#4527a0,stroke-width:2px;

    subgraph Inputs [Inputs — flexible config]
        direction TB
        SPLIT["Split files\nconfig_dut.yaml + config_uvm.yaml"]
        UNIFIED["Unified file\nconfig.yaml"]
        AUTO["Auto-discovery\n*.yaml in CWD"]
    end

    subgraph Phase0 [Config Resolution]
        Resolver[ConfigResolver]:::logic
        Layout[ConfigLayout\nderived from dataclass metadata]:::meta
        RC(ResolvedConfigs\ndut · uvm · unified):::data
        Layout -. derives key sets .-> Resolver
        Resolver --> RC
    end

    subgraph Phase1 [Configuration Loading]
        Loader[ConfigLoader]:::logic
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
        Generator[Generator / Orchestrator]:::logic
        Registry[(GenerationRegistry <br> files · content · context)]:::registry

        subgraph Units [Generation Units — toposorted]
            direction LR
            U1[ParamsPkg]:::unit
            U2[Transaction]:::unit
            U3[Interface]:::unit
            U4[Agents]:::unit
            U5[Sequences]:::unit
            U6[Env]:::unit
            U7[Tests]:::unit
            U8[Top]:::unit

            U1 --> U2 & U3
            U2 & U3 --> U4 & U5
            U4 & U5 --> U6
            U6 & U3 & U4 --> U7
            U3 & U4 --> U8
        end

        Renderer[Jinja2 Renderer]:::logic
        Writer[File Manager]:::logic
        Templates[Templates .j2]
    end

    subgraph Outputs [Generated TB]
        SV_FILES[SystemVerilog Files .sv]:::artifact
    end

    SPLIT & UNIFIED & AUTO --> Resolver
    RC --> Loader
    Loader --> DUT_OBJ & UVM_OBJ
    DUT_OBJ & UVM_OBJ --> Builder
    Builder --> EnvModel

    EnvModel ==> Generator
    Generator -- bootstraps --> Registry
    Generator -- toposort + dispatch --> Units
    Units -- read deps / write outputs --> Registry
    Units --> Renderer
    Templates -.-> Renderer
    Renderer --> Writer
    Writer --> Outputs
```
+

## User-Friendly Regeneration: Preservation of Manual Edits
UVM_PYGEN automatically preserves manual changes made by user. No special markers or protected areas are needed.


## Testbench topology strategy
```mermaid
flowchart LR
    SEQ --> DRV --> RM 
    DRV --> DUT
    RM --> SCB
    DUT--> MON 
    MON --> SCB

```

```mermaid
flowchart LR
    SEQ1 --> DRV1 --> RM 
    RM --> MON1 --> SCB
    SEQ2 --> DRV2 --> DUT
    DUT --> MON2 --> SCB
```