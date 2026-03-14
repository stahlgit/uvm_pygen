"""UVM models for UVM testbench generation."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction


class Component(BaseModel):
    """UVM component definition."""

    name: str
    type: ComponentType
    interface: str | None = None
    direction: Direction | None = None
    mode: AgentMode | None = None  # e.g., "active", "passive"

    # Typed as dict[str, dict] — keys are ComponentType string values
    # e.g., {"driver": {"enabled": true}, "sequencer": {"enabled": true}}
    subcomponents: dict[str, dict[str, Any]] = Field(default_factory=dict)

    inputs: list[str] | None = None
    comparison_method: str | None = None
    input_from: str | None = None
    behavior: str | dict | None = None

    @field_validator("subcomponents", mode="before")
    @classmethod
    def normalise_subcomponents(cls, v: Any) -> dict[str, dict[str, Any]]:
        """Ensure every subcomponent entry is a dict, never None."""
        if not isinstance(v, dict):
            return {}
        return {k: (val if isinstance(val, dict) else {}) for k, val in v.items()}


class TransactionField(BaseModel):
    """Transaction field definition."""

    name: str
    randomize: bool
    default: Any = None


class Sequence(BaseModel):
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


class Coverpoint(BaseModel):
    """Coverage coverpoint definition."""

    name: str
    sample_field: str
    bins: list[dict] | None = None
    type: str = "coverpoint"


class Test(BaseModel):
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
