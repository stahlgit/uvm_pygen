"""UVM models for UVM testbench generation."""

from dataclasses import dataclass, field
from typing import Any

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction


@dataclass
class Component:
    """UVM component definition."""

    name: str
    type: ComponentType
    interface: str | None = None
    direction: Direction | None = None
    mode: AgentMode | None = None  # e.g., "active", "passive"
    subcomponents: dict = field(default_factory=dict)
    inputs: list[str] | None = None
    comparison_method: str | None = None
    input_from: str | None = None
    behavior: str | dict | None = None


@dataclass
class TransactionField:
    """Transaction field definition."""

    name: str
    randomize: bool
    default: Any = None


@dataclass
class Sequence:
    """Sequence definition."""

    name: str
    type: str
    transaction: str | None = None
    abstract: bool = False
    extends: str | None = None
    transaction_count: Any = None
    description: str = ""
    constraints: list[str] | None = None
    directed: bool = False
    randomization: bool = True
    operation_list: list[str] | None = None


@dataclass
class Coverpoint:
    """Coverage coverpoint definition."""

    name: str
    sample_field: str
    bins: list[dict] | None = None
    type: str = "coverpoint"


@dataclass
class Test:
    """UVM test definition."""

    name: str
    type: str
    environment: str | None = None
    abstract: bool = False
    extends: str | None = None
    sequence: str | None = None
    sequences: list[str] | None = None
    transaction_count: int | None = None
    timeout: int | None = None
    description: str | None = None
    build_phase: str = "default"
    run_phase: str = "default"
    coverage_goal: int | None = None
