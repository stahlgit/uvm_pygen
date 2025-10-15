# 
so far only documentation here

### TestBench

```mermaid
flowchart
    subgraph SystemVerilog TestBench
    stimulus_generator
    checker_SW
    scoreboard
    end
    stimulus_generator-->DUT
    DUT-->checker_SW
    DUT-->scoreboard
    CLK-->DUT

``` 

### Simplified UVM hierarchy 
uvm_root
 ├─ uvm_component
 │   ├─ uvm_env
 │   ├─ uvm_test
 │   ├─ [uvm_agent](/docs/uvm_components/uvm_agent.md)
 │   │   ├─ uvm_driver
 │   │   ├─ uvm_sequencer
 │   │   └─ uvm_monitor
 │   ├─ uvm_scoreboard
 │   └─ uvm_subscriber
 │
 └─ uvm_object
     ├─ uvm_transaction
     │   └─ uvm_sequence_item
     │       └─ uvm_sequence
     ├─ uvm_config_db
     ├─ uvm_resource
     ├─ uvm_event
     ├─ uvm_factory
     └─ uvm_callback




```mermaid
flowchart 
    subgraph top
    subgraph TestBench
        virtual_interface
    end
    virtual_interface-->Interface
    Interface---DUT
    end

```

<details>
<summary> <b>uv_root</b> </summary>

- <details>
    <summary>uvm_component</summary>

    - <details>
        <summary>uvm_env</summary>
      </details>
    
    - <details>
        <summary>uvm_test</summary>
        vytvára inštanciu UVM prostredia (uvm_env) a štartuje sekvenciu(uvm_sequence)
      </details>
    
    - <details>
        <summary>**uvm_agent**</summary>
        
        * <details>
            <summary>uvm_driver</summary>
            driver
          </details>
        * <details>
            <summary>uvm_sequencer</summary>
            sequencer
          </details>
        </details>
    
    - <details>
        <summary>uvm_scoreboard</summary>
      </details>
    
    - <details>
        <summary>uvm_subscriber</summary>
      </details>

  </details>

- <details>
    <summary>uvm_object</summary>
    base for everything non-component
  </details>

</details>