"""YAML layout registry — single source of truth for DUT / UVM top-level keys.

Every Pydantic model that maps to a top-level YAML section declares its section
membership via ``json_schema_extra``:

    class DUTInfo(BaseModel):
        model_config = ConfigDict(json_schema_extra={"yaml_section": "dut", "yaml_key": "dut"})

``ConfigLayout`` introspects all registered models at import time and exposes
the derived key sets to the rest of the codebase — no hardcoded strings outside
of the dataclass files themselves.

Sections:
    "dut": Keys that belong in a DUT YAML (or the DUT half of a unified file).
    "uvm": Keys that belong in a UVM YAML (or the UVM half of a unified file).
"""

from __future__ import annotations

from pydantic import BaseModel

from uvm_pygen.models.config_schema.dut_dataclass import (
    Constraints,
    DUTInfo,
    EnumType,
    Parameter,
    Port,
)
from uvm_pygen.models.config_schema.uvm_dataclass import (
    Component,
    Coverpoint,
    Sequence,
    Test,
    TransactionField,
    VerificationInfo,
)


def _yaml_key(model: type[BaseModel]) -> str | None:
    """Return the yaml_key declared in a model's json_schema_extra, or None.

    Args:
        model: A Pydantic BaseModel class.

    Returns:
        The yaml_key value from json_schema_extra, or None if not found.
    """
    extra = model.model_config.get("json_schema_extra") or {}
    return extra.get("yaml_key")


def _yaml_section(model: type[BaseModel]) -> str | None:
    """Return the yaml_section declared in a model's json_schema_extra, or None.

    Args:
        model: A Pydantic BaseModel class.

    Returns:
        The yaml_section value from json_schema_extra, or None if not found.
    """
    extra = model.model_config.get("json_schema_extra") or {}
    return extra.get("yaml_section")


# All top-level models that carry yaml_section / yaml_key metadata.
_ALL_MODELS: tuple[type[BaseModel], ...] = (
    # DUT section
    DUTInfo,
    Parameter,
    EnumType,
    Port,
    Constraints,
    # UVM section
    Component,
    TransactionField,
    Sequence,
    Coverpoint,
    Test,
    VerificationInfo,
)


class ConfigLayout:
    """Derived YAML layout — built once from the dataclass metadata.

    Attributes:
        dut_keys: All top-level YAML keys that belong to a DUT config file.
        uvm_keys: All top-level YAML keys that belong to a UVM config file.
        dut_required_keys: Subset of dut_keys that must be present for a file
            to be recognised as a DUT config (used for unified-file detection).
        uvm_required_keys: Subset of uvm_keys that must be present for a file
            to be recognised as a UVM config.
    """

    def __init__(self) -> None:
        """Introspect all models and build the key sets."""
        dut: set[str] = set()
        uvm: set[str] = set()

        for model in _ALL_MODELS:
            key = _yaml_key(model)
            section = _yaml_section(model)
            if key is None or section is None:
                continue
            if section == "dut":
                dut.add(key)
            elif section == "uvm":
                uvm.add(key)

        self.dut_keys: frozenset[str] = frozenset(dut)
        self.uvm_keys: frozenset[str] = frozenset(uvm)

        # "Required" keys are those whose models are marked required=True.
        # Everything else is optional (present only in some configs).
        self.dut_required_keys: frozenset[str] = self._required_keys("dut")
        self.uvm_required_keys: frozenset[str] = self._required_keys("uvm")

    def _required_keys(self, section: str) -> frozenset[str]:
        """Extract required keys for a given section.

        Args:
            section: The YAML section name ("dut" or "uvm").

        Returns:
            A frozenset of required keys for the section.
        """
        keys: set[str] = set()
        for model in _ALL_MODELS:
            extra = model.model_config.get("json_schema_extra") or {}
            if extra.get("yaml_section") == section and extra.get("required", False):
                key = extra.get("yaml_key")
                if key:
                    keys.add(key)
        return frozenset(keys)


# Module-level singleton — imported by ConfigResolver and anywhere else that needs to reason about the YAML layout without touching raw strings.
layout = ConfigLayout()
