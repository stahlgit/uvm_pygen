import sys

from uvm_pygen.services.loader import ConfigLoader
from uvm_pygen.services.model_builder.model_builder import ModelBuilder

if __name__ == "__main__":
    ### PHASE 1 : LOAD AND VALIDATE CONFIGURATIONS ###
    # Load configurations
    loader = ConfigLoader(dut_config_path="config_dut.yaml", uvm_config_path="config_uvm.yaml")

    # Validate
    if not loader.validate():
        print("\n❌ Configuration validation failed!")
        sys.exit(1)

    # Print summary
    loader.summary()

    ### PHASE 2 : BUILD ENVIRONMENT MODEL ###
    builder = ModelBuilder(loader)

    """
    env_model = EnvModel.create_from_configs(loader.dut, loader.uvm)

    # 4. Display environment model summary (includes agents)
    print("\n" + "=" * 70)
    print("ENVIRONMENT MODEL WITH AGENTS")
    print("=" * 70)
    loader.env_model.summary()

    # 5. Test individual agent access
    print("\n" + "=" * 70)
    print("AGENT ACCESS TEST")
    print("=" * 70)

    alu_agent = loader.env_model.get_agent("alu_agent")
    if alu_agent:
        print(f"\n✓ Found agent: {alu_agent.name}")
        print(f"  Mode: {alu_agent.mode}")
        print(f"  Active: {alu_agent.is_active()}")
        print(f"  Interface ports: {len(alu_agent.get_all_ports())}")
        print(f"  Enum types: {list(alu_agent.get_enum_types().keys())}")

        if alu_agent.driver:
            print("\n  Driver:")
            print(f"    Name: {alu_agent.driver.name}")
            print(f"    Driven ports: {[p.name for p in alu_agent.driver.driven_ports]}")

        if alu_agent.monitor:
            print("\n  Monitor:")
            print(f"    Name: {alu_agent.monitor.name}")
            print(f"    Monitored ports: {[p.name for p in alu_agent.monitor.monitored_ports]}")

        if alu_agent.sequencer:
            print("\n  Sequencer:")
            print(f"    Name: {alu_agent.sequencer.name}")
            print(f"    Transaction type: {alu_agent.sequencer.transaction_type}")

    output_agent = loader.env_model.get_agent("output_agent")
    if output_agent:
        print(f"\n✓ Found agent: {output_agent.name}")
        print(f"  Mode: {output_agent.mode}")
        print(f"  Active: {output_agent.is_active()}")
        print(f"  Interface direction: {output_agent.interface.direction}")
        print(f"  Has driver: {output_agent.driver is not None}")
        print(f"  Has monitor: {output_agent.monitor is not None}")

    # 6. Test agent filtering
    print("\n" + "=" * 70)
    print("AGENT FILTERING TEST")
    print("=" * 70)

    active_agents = loader.env_model.get_active_agents()
    passive_agents = loader.env_model.get_passive_agents()

    print(f"\nActive agents ({len(active_agents)}):")
    for agent in active_agents:
        print(f"  - {agent.name}")

    print(f"\nPassive agents ({len(passive_agents)}):")
    for agent in passive_agents:
        print(f"  - {agent.name}")

    print("\n" + "=" * 70)
    print("✓ Agent model test completed successfully!")
    print("=" * 70)
    """
