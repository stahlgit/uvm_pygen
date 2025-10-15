# UVM_AGENT

```mermaid
flowchart LR
    subgraph uvm_agent
    uvm_monitor
    uvm_sequencer-->uvm_driver
    end

    note over uvm_monitor
        This is a passive component.
        It samples the DUT pins
        and converts them to transactions.
    end

    note right of uvm_driver
        The driver receives
        sequence items and
        drives the physical interface.
    end
    
    DUT-->uvm_monitor
    uvm_driver-->DUT
```
