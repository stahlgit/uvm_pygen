"""Configuration Loader Module."""

from __future__ import annotations

from pathlib import Path

from uvm_pygen.services.config_parser.config_resolver import ConfigResolver
from uvm_pygen.services.config_parser.dut_config import DUTConfiguration
from uvm_pygen.services.config_parser.uvm_config import UVMConfiguration
from uvm_pygen.services.utils.logger import logger


class ConfigLoader:
    """Main configuration loader.

    Loads both DUT and UVM configs and provides a unified validation interface.

    Accepts three calling modes:
        Split files (original behaviour):
            ConfigLoader(dut_config_path="config_dut.yaml", uvm_config_path="config_uvm.yaml")

        Unified file:
            ConfigLoader(unified_config_path="config.yaml")

        Pre-split raw dicts (used internally by the unified path):
            ConfigLoader(dut_raw={...}, uvm_raw={...})

    Pydantic models validate field-level constraints on construction inside
    DUTConfiguration / UVMConfiguration._parse(). This class aggregates
    the cross-object errors returned by their validate() methods.
    """

    def __init__(
        self,
        dut_config_path: str | Path | None = None,
        uvm_config_path: str | Path | None = None,
        unified_config_path: str | Path | None = None,
        dut_raw: dict | None = None,
        uvm_raw: dict | None = None,
    ) -> None:
        """Initialize and load configurations.

        Args:
            dut_config_path: Path to DUT configuration file.
            uvm_config_path: Path to UVM configuration file.
            unified_config_path: Path to unified configuration file.
            dut_raw: Pre-parsed DUT configuration dictionary.
            uvm_raw: Pre-parsed UVM configuration dictionary.

        Raises:
            ValueError: If conflicting arguments are supplied, or if a config file
                fails Pydantic field validation during parsing.
        """
        has_split = dut_config_path is not None or uvm_config_path is not None
        has_unified = unified_config_path is not None
        has_raw = dut_raw is not None or uvm_raw is not None

        if sum([has_split, has_unified, has_raw]) > 1:
            raise ValueError(
                "ConfigLoader: supply exactly one of "
                "(dut_config_path/uvm_config_path), (unified_config_path), or (dut_raw/uvm_raw)."
            )

        if has_unified:
            self._load_from_unified(Path(unified_config_path))
        elif has_raw:
            self._load_from_raw(dut_raw or {}, uvm_raw or {})
        else:
            self._load_split(dut_config_path, uvm_config_path)

        logger.info("✓ Configuration loaded successfully")

    def validate(self) -> bool:
        """Run cross-object validation on both configs.

        Returns:
            True if no errors were found, False otherwise.
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

    def _load_split(
        self,
        dut_config_path: str | Path | None,
        uvm_config_path: str | Path | None,
    ) -> None:
        """Load configurations from separate DUT and UVM files.

        Args:
            dut_config_path: Path to DUT configuration file.
            uvm_config_path: Path to UVM configuration file.

        Raises:
            ValueError: If either path is None.
        """
        if dut_config_path is None or uvm_config_path is None:
            raise ValueError(
                "Both dut_config_path and uvm_config_path must be provided when not using a unified config."
            )
        logger.info(f"Loading DUT config: {dut_config_path}")
        self.dut = DUTConfiguration(dut_config_path)

        logger.info(f"Loading UVM config: {uvm_config_path}")
        self.uvm = UVMConfiguration(uvm_config_path)

    def _load_from_unified(self, unified_path: Path) -> None:
        """Load and split a unified config file, then delegate to _load_from_raw.

        Args:
            unified_path: Path to unified configuration file.
        """
        logger.info(f"Loading unified config: {unified_path}")
        dut_raw, uvm_raw = ConfigResolver().split_unified(unified_path)
        self._load_from_raw(dut_raw, uvm_raw, source_label=str(unified_path))

    def _load_from_raw(
        self,
        dut_raw: dict,
        uvm_raw: dict,
        source_label: str = "<in-memory>",
    ) -> None:
        """Instantiate DUTConfiguration and UVMConfiguration from pre-parsed dicts.

        Args:
            dut_raw: Pre-parsed DUT configuration dictionary.
            uvm_raw: Pre-parsed UVM configuration dictionary.
            source_label: Label indicating the source of the configuration.
                Defaults to "<in-memory>".
        """
        logger.info(f"Parsing DUT section from: {source_label}")
        self.dut = DUTConfiguration.from_dict(dut_raw, source_label=source_label)

        logger.info(f"Parsing UVM section from: {source_label}")
        self.uvm = UVMConfiguration.from_dict(uvm_raw, source_label=source_label)
