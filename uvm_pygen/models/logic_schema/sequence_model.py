from dataclasses import dataclass

from uvm_pygen.models.logic_schema.transaction_model import SvConstraint


@dataclass
class SequenceModel:
    """Model pre jednu UVM sekvenciu."""

    name: str
    base_class: str  # napr. "uvm_sequence" alebo "alu_base_sequence"
    transaction_type: str
    constraints: list[SvConstraint]  # Tu už použijeme tvoju existujúcu triedu pre constraints
    body_code: list[str] | None = None  # Pre vlastný kód v body()
