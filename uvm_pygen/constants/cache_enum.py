"""
Project Name: uvm_pygen
File Name: cache_enum.py
Description: Cache constants for UVM-Pygen.
Author: Peter Stahl (xstahl01@stud.fit.vut.cz)
Date: 2026-05-11
"""

from enum import StrEnum, auto


class ConfigMode(StrEnum):
    """Defines the mode of configuration used in UVM-Pygen."""

    SPLIT = auto()  # Separate DUT and UVM config files
    UNIFIED = auto()  # Single config file containing both DUT and UVM sections
