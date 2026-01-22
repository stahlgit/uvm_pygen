"""Main script to generate UVM verification environment based on configurations."""

import sys

from uvm_pygen.services.config_parser.config_loader import ConfigLoader
from uvm_pygen.services.generation.uvm_generator import UVMGenerator
from uvm_pygen.services.model_builder.model_builder import ModelBuilder


def main():
    ### PHASE 1 : LOAD AND VALIDATE CONFIGURATIONS ###
    loader = ConfigLoader(dut_config_path="config_dut.yaml", uvm_config_path="config_uvm.yaml")

    if not loader.validate():
        print("\n❌ Configuration validation failed!")
        sys.exit(1)

    # Summary maybe for some verbose mode or debugging ?
    # loader.summary()

    ### PHASE 2 : BUILD ENVIRONMENT MODEL ###
    builder = ModelBuilder(loader)
    env_model = builder.build()

    ### PHASE 3 : GENERATE UVM VERIFICATION ENVIRONMENT ###
    generator = UVMGenerator(env_model, output_dir="my_tb_verif")
    generator.generate_all()


if __name__ == "__main__":
    main()
