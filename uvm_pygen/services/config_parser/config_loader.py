"""Configuration Loader Module."""

from pathlib import Path

from uvm_pygen.services.config_parser.dut_config import DUTConfiguration
from uvm_pygen.services.config_parser.uvm_config import UVMConfiguration
from uvm_pygen.services.utils.logger import logger


class ConfigLoader:
    """Main configuration loader.

    Loads both DUT and UVM configs and provides a unified validation interface.
    Pydantic models validate field-level constraints on construction inside
    DUTConfiguration / UVMConfiguration._parse(); this class aggregates the
    cross-object errors returned by their validate() methods.
    """

    def __init__(self, dut_config_path: str | Path, uvm_config_path: str | Path) -> None:
        """Initialize and load configurations.

        Raises:
            ValueError: If either config file fails Pydantic field validation
                        during parsing (bad types, missing required fields, etc.).
                        The message will identify the exact file and field.
        """
        logger.info(f"Loading DUT config: {dut_config_path}")
        self.dut = DUTConfiguration(dut_config_path)

        logger.info(f"Loading UVM config: {uvm_config_path}")
        self.uvm = UVMConfiguration(uvm_config_path)

        logger.info("✓ Configuration loaded successfully")

    def validate(self) -> bool:
        """Run cross-object validation on both configs.

        Field-level errors are already caught during __init__ (Pydantic raises
        immediately on bad data).  This method checks higher-level consistency:
        enum references, required port groups, agent sub-components, sequence
        parent chains, and transaction name coherence.

        Returns:
            bool: True if no errors were found, False otherwise.
        """
        logger.debug("Validating configurations...")

        errors: list[str] = self.dut.validate() + self.uvm.validate()
        if errors:
            logger.error("❌ Validation errors:")
            for err in errors:
                logger.error(f"  - {err}")
            return False

        logger.info("✓ Configuration validation passed")
        return True

    def summary(self) -> None:
        """Print a human-readable configuration summary."""
        print("\n" + "=" * 60)
        print("CONFIGURATION SUMMARY")
        print("=" * 60)

        print(f"\nDUT: {self.dut.dut_info.name}")
        print(f"  Description: {self.dut.dut_info.description}")
        print(f"  Data Width:  {self.dut.dut_info.data_width} bits")
        print(f"  Language:    {self.dut.dut_info.language}")

        print(f"\nEnums: {len(self.dut.enums)}")
        for enum_name, enum_type in self.dut.enums.items():
            print(f"  - {enum_name}: {len(enum_type.values)} values")

        print(f"\nPorts: {len(self.dut.ports)}")
        print(f"  - Control:    {len(self.dut.get_control_ports())}")
        print(f"  - Data Input: {len(self.dut.get_data_input_ports())}")
        print(f"  - Output:     {len(self.dut.get_data_output_ports())}")

        print(f"\nUVM Environment: {self.uvm.env_name}")
        print(f"  Components: {len(self.uvm.components)}")
        print(f"  Sequences:  {len(self.uvm.sequences)}")

        print("=" * 60 + "\n")
