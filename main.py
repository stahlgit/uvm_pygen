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
    # loader.summary()

    ### PHASE 2 : BUILD ENVIRONMENT MODEL ###
    builder = ModelBuilder(loader)
    env_model = builder.build()
    print("\n" + "=" * 70)
    print("INTERNAL MODEL SUMMARY")
    print("=" * 70)

    print(f"Transaction: {env_model.transaction.class_name}")
    print(f"  - Variables: {[v.name for v in env_model.transaction.variables]}")

    print(f"\nInterface: {env_model.interfaces[0].name}")
    print(f"  - Ports: {len(env_model.interfaces[0].ports)}")

    print(f"\nAgents: {len(env_model.agents)}")
    for agent in env_model.agents:
        print(f"  - {agent.name} ({agent.active})")

    if env_model.scoreboard:
        print(f"\nScoreboard: {env_model.scoreboard.name}")
        print(f"  - Exports: {env_model.scoreboard.analysis_exports}")

    print(f"\nSequences: {len(env_model.sequences)}")
    for seq in env_model.sequences:
        print(f"  - {seq.name} (Base: {seq.base_class})")
