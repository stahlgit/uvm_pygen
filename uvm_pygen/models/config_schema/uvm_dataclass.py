"""UVM models for UVM testbench generation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from uvm_pygen.constants.uvm_enum import AgentMode, ComponentType, Direction


class Component(BaseModel):
    """UVM component definition.

    Top-level YAML key: ``environment`` → ``components``
    The owning key is ``environment`` (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "environment", "required": True},
    )

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
    """Transaction field definition.

    Top-level YAML key: ``transactions``  (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "transactions", "required": True},
    )

    name: str
    randomize: bool
    default: Any = None


class Sequence(BaseModel):
    """Sequence definition.

    Top-level YAML key: ``sequences``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "sequences"},
    )

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
    """Coverage coverpoint definition.

    Top-level YAML key: ``coverage``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "coverage"},
    )

    name: str
    sample_field: str
    bins: list[dict] | None = None
    type: str = "coverpoint"


class Test(BaseModel):
    """UVM test definition.

    Top-level YAML key: ``tests``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "tests"},
    )

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


class VerificationInfo(BaseModel):
    """Verification environment metadata.

    Top-level YAML key: ``verification``  (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "verification", "required": True},
    )

    project_name: str = "uvm_project"
    testbench_name: str = "tb_top"
    uvm_version: str = "1.2"


class SimulationConfig(BaseModel):
    """Simulation options.

    Top-level YAML key: ``simulation``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "simulation"},
    )


class RandomizationConfig(BaseModel):
    """Randomization control.

    Top-level YAML key: ``randomization``
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "randomization"},
    )
