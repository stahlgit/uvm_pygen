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

from uvm_pygen.constants.config_alliases import YAML_KEY_ALIAS_GROUPS
from uvm_pygen.models.config_schema.dut_dataclass import (
    Constraints,
    DUTInfo,
    EnumType,
    Parameter,
    Port,
)
from uvm_pygen.models.config_schema.uvm_dataclass import (
    AgentConfig,
    Connection,
    Coverpoint,
    InterfaceDeclaration,
    ReferenceModelImplementation,
    Sequence,
    Test,
    TransactionField,
    VerificationInfo,
)


def _yaml_key(model: type[BaseModel]) -> str | None:
    extra = model.model_config.get("json_schema_extra") or {}
    return extra.get("yaml_key")


def _yaml_section(model: type[BaseModel]) -> str | None:
    extra = model.model_config.get("json_schema_extra") or {}
    return extra.get("yaml_section")


def _expand_with_aliases(keys: set[str]) -> frozenset[str]:
    """Expand each key with its aliases from YAML_KEY_ALIAS_GROUPS."""
    expanded = set(keys)
    for key in keys:
        expanded |= YAML_KEY_ALIAS_GROUPS.get(key, frozenset())
    return frozenset(expanded)


# All top-level models that carry yaml_section / yaml_key metadata.
_ALL_MODELS: tuple[type[BaseModel], ...] = (
    # DUT section
    DUTInfo,
    Parameter,
    EnumType,
    Port,
    Constraints,
    # UVM section
    InterfaceDeclaration,
    AgentConfig,
    TransactionField,
    Sequence,
    Coverpoint,
    Test,
    ReferenceModelImplementation,
    Connection,
    VerificationInfo,
)


class ConfigLayout:
    """Derived YAML layout — built once from the dataclass metadata.

    Attributes:
        dut_keys: All top-level YAML keys (including aliases) for a DUT config.
        uvm_keys: All top-level YAML keys (including aliases) for a UVM config.
        dut_required_keys: Expanded flat set of required DUT keys (all aliases included).
        uvm_required_keys: Expanded flat set of required UVM keys (all aliases included).
        dut_required_key_groups: Tuple of alias groups; at least one key per group must
            be present for the DUT section to be valid.
        uvm_required_key_groups: Same for the UVM section.
    """

    def __init__(self) -> None:
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

        self.dut_keys: frozenset[str] = _expand_with_aliases(dut)
        self.uvm_keys: frozenset[str] = _expand_with_aliases(uvm)

        raw_dut_req = self._required_keys_raw("dut")
        raw_uvm_req = self._required_keys_raw("uvm")

        self.dut_required_keys: frozenset[str] = _expand_with_aliases(raw_dut_req)
        self.uvm_required_keys: frozenset[str] = _expand_with_aliases(raw_uvm_req)

        self.dut_required_key_groups: tuple[frozenset[str], ...] = self._build_required_key_groups(raw_dut_req)
        self.uvm_required_key_groups: tuple[frozenset[str], ...] = self._build_required_key_groups(raw_uvm_req)

    def _required_keys_raw(self, section: str) -> set[str]:
        """Return canonical required keys for a section (no alias expansion)."""
        keys: set[str] = set()
        for model in _ALL_MODELS:
            extra = model.model_config.get("json_schema_extra") or {}
            if extra.get("yaml_section") == section and extra.get("required", False):
                key = extra.get("yaml_key")
                if key:
                    keys.add(key)
        return keys

    @staticmethod
    def _build_required_key_groups(raw_keys: set[str]) -> tuple[frozenset[str], ...]:
        """Build alias groups for required keys.

        Each group contains all accepted forms of the key; at least one must
        be present in the YAML for the requirement to be satisfied.
        """
        return tuple(YAML_KEY_ALIAS_GROUPS.get(key, frozenset({key})) for key in raw_keys)


# Module-level singleton — imported by ConfigResolver and anywhere else that needs to reason about the YAML layout without touching raw strings.
layout = ConfigLayout()
