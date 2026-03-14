"""Utility types for Pydantic models, such as non-empty strings and lists."""

from typing import Annotated

from pydantic import Field, StringConstraints

# --- Reusable Types ---
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonEmptyList = Annotated[list[str], Field(min_length=1)]
