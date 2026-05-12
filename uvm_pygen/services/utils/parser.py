"""
Project Name: uvm_pygen
File Name: parser.py
Description: Utility parser for command-line arguments
Author: Peter Stahl (xstahl01@stud.fit.vut.cz)
Date: 2026-05-11
"""

import argparse


def parse_args():
    """Defines and parses command-line arguments."""
    parser = argparse.ArgumentParser(description="UVM PyGen - Logic Model Generator")

    ### DEBUG FLAG ###
    parser.add_argument("--debug", action="store_true", help="Enable detailed debug logging in console and file")

    ### CONFIGURATION FILE FLAGS ###
    parser.add_argument(
        "--dut-config",
        metavar="FILE",
        default=None,
        help=(
            "Path to the DUT configuration YAML file. "
            "When omitted, UVM_PYGEN auto-discovers a '*dut*' YAML in the current directory."
        ),
    )
    parser.add_argument(
        "--uvm-config",
        metavar="FILE",
        default=None,
        help=(
            "Path to the UVM configuration YAML file. "
            "When omitted, UVM_PYGEN auto-discovers a '*uvm*' YAML in the current directory."
        ),
    )

    parser.add_argument(
        "--config",
        metavar="FILE",
        default=None,
        help=(
            "Path to a unified configuration YAML file containing both DUT and UVM sections. "
            "Mutually exclusive with --dut-config / --uvm-config."
        ),
    )

    parser.add_argument(
        "--use-cache", action="store_true", help="Use cached config paths from previous run (.uvm_pygen/cache.json)."
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Re-seed the merge cache from the current output directory before generating. "
            "Use this once after a cold start (missing cache) to restore three-way merge capability."
        ),
    )

    args = parser.parse_args()

    # Enforce mutual exclusivity of --config with --dut-config and --uvm-config
    if args.config and (args.dut_config or args.uvm_config):
        parser.error("--config cannot be used together with --dut-config or --uvm-config.")

    # --use-cache is mutually exclusive with any explicit config flag
    if args.use_cache and (args.config or args.dut_config or args.uvm_config):
        parser.error("--use-cache cannot be combined with --config, --dut-config, or --uvm-config.")

    return args
