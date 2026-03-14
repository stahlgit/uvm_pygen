"""Model for UVM sequence generation."""

from pydantic import BaseModel, ConfigDict, Field

from uvm_pygen.models.logic_schema.transaction_model import SvConstraint
from uvm_pygen.models.utils.util_annotation import NonEmptyStr


class SequenceModel(BaseModel):
    """Model for a single UVM sequence.

    Built by ModelBuilder from the UVM config Sequence dataclass and enriched
    with constraint objects resolved from the transaction model.  Immutable
    after construction — generation units only read it.

    Fields:
        name:             SystemVerilog class name for the sequence.
        base_class:       Parent class, e.g. "uvm_sequence" or "alu_base_sequence".
        transaction_type: Type name of the transaction this sequence creates,
                          e.g. "alu_transaction".
        constraints:      SvConstraint objects to emit inside the sequence class.
        body_code:        Optional list of raw SV lines to emit inside body().
                          None means the template uses its default body implementation.
    """

    model_config = ConfigDict(frozen=True)

    name: NonEmptyStr
    base_class: NonEmptyStr
    transaction_type: NonEmptyStr
    constraints: list[SvConstraint] = Field(default_factory=list)
    body_code: list[str] | None = None

    @property
    def has_custom_body(self) -> bool:
        """Return True if explicit body_code lines were provided."""
        return bool(self.body_code)

    @property
    def is_base(self) -> bool:
        """Return True if this sequence inherits directly from uvm_sequence."""
        return self.base_class == "uvm_sequence"
