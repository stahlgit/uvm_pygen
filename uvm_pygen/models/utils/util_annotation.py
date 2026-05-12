"""
Project Name: uvm_pygen
File Name: util_annotation.py
Description: Utility types for Pydantic models, such as non-empty strings and lists.
Author: Peter Stahl (xstahl01@stud.fit.vut.cz)
Date: 2026-05-11
"""

from typing import Annotated

from pydantic import Field, StringConstraints

# --- Reusable Types ---
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonEmptyList = Annotated[list[str], Field(min_length=1)]
