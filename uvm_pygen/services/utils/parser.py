"""Utility parser for command-line arguments."""

import argparse


def parse_args():
    """Defines and parses command-line arguments."""
    parser = argparse.ArgumentParser(description="UVM PyGen - Logic Model Generator")
    parser.add_argument("--debug", action="store_true", help="Enable detailed debug logging in console and file")
    return parser.parse_args()
