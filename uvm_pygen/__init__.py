"""Main script to generate UVM verification environment based on configurations."""

import sys

from uvm_pygen.services.config_parser.config_cache import read_cache, write_cache
from uvm_pygen.services.config_parser.config_loader import ConfigLoader
from uvm_pygen.services.config_parser.config_resolver import ConfigResolver, ResolvedConfigs
from uvm_pygen.services.generation.generator import Generator
from uvm_pygen.services.model_builder.model_builder import ModelBuilder
from uvm_pygen.services.utils.logger import logger, set_debug_mode
from uvm_pygen.services.utils.parser import parse_args


def run():
    """Main function to orchestrate the UVM environment generation process."""
    args = parse_args()

    if args.debug:
        set_debug_mode(True)
        logger.debug("[bold magenta]Debug mode enabled[/bold magenta]")

    ### PHASE 1 : LOAD AND VALIDATE CONFIGURATIONS ###
    if args.use_cache:
        resolved: ResolvedConfigs = read_cache()
    else:
        resolved: ResolvedConfigs = ConfigResolver().resolve(
            dut_config=args.dut_config,
            uvm_config=args.uvm_config,
            unified_config=args.config,
        )

    if resolved.is_unified:
        loader = ConfigLoader(unified_config_path=resolved.unified)
    elif resolved.is_split:
        loader = ConfigLoader(dut_config_path=resolved.dut, uvm_config_path=resolved.uvm)
    else:
        logger.error(
            "Could not locate configuration files. "
            "Pass --config (unified) or --dut-config / --uvm-config explicitly, "
            "or place matching YAML files in the working directory."
        )
        sys.exit(1)

    if not loader.validate():
        logger.error("Configuration validation failed. Please check the provided YAML files for errors.")
        sys.exit(1)

    write_cache(resolved)

    ### PHASE 2 : BUILD ENVIRONMENT MODEL ###
    builder = ModelBuilder(loader)
    env_model = builder.build()

    ### PHASE 3 : GENERATE UVM VERIFICATION ENVIRONMENT ###
    generator = Generator(env_model)
    generator.generate_all()
