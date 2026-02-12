from dataclasses import dataclass


@dataclass
class SvVariable:
    """Reprezentuje jednu premennú v SystemVerilogu (člen transakcie)."""

    name: str
    sv_type: str  # Napr. "logic [7:0]" alebo "operation_t"
    is_rand: bool  # Pridá kľúčové slovo "rand"
    default_value: str | None = None  # Napr. "0" alebo "ADD"
    comment: str = ""
    #TODO: is_enum ?


@dataclass
class SvConstraint:
    """Reprezentuje SystemVerilog constraint blok."""

    name: str
    body: list[str]  # Riadky kódu vo vnútri constraintu


@dataclass
class TransactionModel:
    """Hotový model pre vygenerovanie alu_seq_item.sv"""

    class_name: str
    variables: list[SvVariable]
    constraints: list[SvConstraint]
    macros: list[str]  # Napr. `uvm_object_utils_begin` polia
