"""UVM models for UVM testbench generation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.functional_validators import model_validator

from uvm_pygen.constants.uvm_enum import (
    AgentMode,
    ComponentType,
    ReferenceModelImplEnum,
    ReferenceModelStrategy,
)


class InterfaceDeclaration(BaseModel):
    """Interface definition.

    Top-level YAML key: ``environment`` → ``interfaces``
    The owning key is ``environment`` (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "environment", "required": True},
    )

    name: str
    ports: list[str]


class AgentConfig(BaseModel):
    """Agent-specific configuration.

    Top-level YAML key: ``environment`` → ``agents``
    The owning key is ``environment`` (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "environment", "required": True},
    )

    name: str
    mode: AgentMode
    interface: str  # validated in ModelBuilder to ensure it matches an interface declaration
    transaction: str | None = None  # validated in ModelBuilder to ensure it matches a transaction declaration
    components: list[ComponentType]


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


class TransactionConfig(BaseModel):
    """Transaction configuration.

    Top-level YAML key: ``transactions``  (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "transactions", "required": True},
    )

    name: str
    base_class: str = "uvm_sequence_item"
    field_overrides: list[TransactionField] = []


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


class ReferenceModelImplementation(BaseModel):
    """Reference model implementation details."""

    model_config = ConfigDict(frozen=True)

    type: ReferenceModelImplEnum = ReferenceModelImplEnum.SV_CLASS
    function: str | None = None  # required for DPI, ignored for SV_CLASS
    header: str | None = None  # required for DPI, ignored for SV_CLASS

    @model_validator(mode="after")
    def dpi_requires_function_and_header(self) -> ReferenceModelImplementation:
        """Ensure that if the implementation type is DPI_EXTERN, both function and header are provided."""
        if self.type == ReferenceModelImplEnum.DPI_EXTERN:
            if not self.function:
                raise ValueError("dpi_extern implementation requires 'function' field")
            if not self.header:
                raise ValueError("dpi_extern implementation requires 'header' field")
        return self


class Connection(BaseModel):
    """Connection between DUT and reference model endpoints."""

    model_config = ConfigDict(frozen=True)
    from_endpoint: str = Field(alias="from")
    to_endpoint: str = Field(alias="to")
    transaction: str | None = None


class ReferenceModelConfig(BaseModel):
    """Reference model configuration.

    Top-level YAML key: ``environment`` → ``reference_model``
    The owning key is ``environment`` (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "environment"},
    )

    strategy: ReferenceModelStrategy = ReferenceModelStrategy.NO_REFERENCE_MODEL
    implementation: ReferenceModelImplementation = ReferenceModelImplementation()
    connects: list[Connection] = []

    @field_validator("implementation", mode="before")
    @classmethod
    def coerce_implementation(cls, v):
        """Accept shorthand string 'sv_class' as well as full dict."""
        if isinstance(v, str):
            return {"type": v}
        return v


class VerificationInfo(BaseModel):
    """Verification environment metadata.

    Top-level YAML key: ``verification``  (required — its presence identifies a UVM config).
    """

    model_config = ConfigDict(
        json_schema_extra={"yaml_section": "uvm", "yaml_key": "verification", "required": True},
    )

    project_name: str = "uvm_project"
    testbench_name: str = "tb_top"


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
