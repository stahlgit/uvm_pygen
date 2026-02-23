"""Configuration Loader Module."""

from pathlib import Path

from uvm_pygen.services.config_parser.dut_config import DUTConfiguration
from uvm_pygen.services.config_parser.uvm_config import UVMConfiguration
from uvm_pygen.services.utils.logger import logger


class ConfigLoader:
    """Main configuration loader.

    Loads both DUT and UVM configs and provides unified interface
    """

    def __init__(self, dut_config_path: str | Path, uvm_config_path: str | Path) -> None:
        """Initialize and load configurations."""
        logger.info(f"Loading DUT config: {dut_config_path}")
        self.dut = DUTConfiguration(dut_config_path)

        logger.info(f"Loading UVM config: {uvm_config_path}")
        self.uvm = UVMConfiguration(uvm_config_path)

        logger.info("✓ Configuration loaded successfully")

    def validate(self) -> bool:
        """Validate configuration consistency."""
        logger.debug("Validating configurations...")

        all_errors: list[str] | None = self.dut.validate().append(self.uvm.validate())
        if all_errors:
            logger.error("❌ Validation errors:")
            for err in all_errors:
                logger.error(f"  - {err}")
            return False

        logger.info("✓ Configuration validation passed")
        return True

    def summary(self) -> None:
        """Print configuration summary."""
        print("\n" + "=" * 60)
        print("CONFIGURATION SUMMARY")
        print("=" * 60)

        print(f"\nDUT: {self.dut.dut_info.name}")
        print(f"  Description: {self.dut.dut_info.description}")
        print(f"  Data Width: {self.dut.dut_info.data_width} bits")
        print(f"  Language: {self.dut.dut_info.language}")

        print(f"\nEnums: {len(self.dut.enums)}")
        for enum_name, enum_type in self.dut.enums.items():
            print(f"  - {enum_name}: {len(enum_type.values)} values")

        print(f"\nPorts: {len(self.dut.ports)}")
        print(f"  - Control: {len(self.dut.get_control_ports())}")
        print(f"  - Data Input: {len(self.dut.get_data_input_ports())}")
        print(f"  - Output: {len(self.dut.get_data_output_ports())}")

        print(f"\nUVM Environment: {self.uvm.env_name}")
        print(f"  Components: {len(self.uvm.components)}")
        print(f"  Sequences: {len(self.uvm.sequences)}")

        print("=" * 60 + "\n")
