"""Model for scoreboard generation."""

from pydantic import BaseModel, ConfigDict, Field

from uvm_pygen.models.utils.util_annotation import NonEmptyStr


class ScoreboardExport(BaseModel):
    """Represents a single analysis export port of the scoreboard."""

    port_name: str  # e.g. "write_actual_export"
    imp_suffix: str  # e.g. "_write_actual"  (for `uvm_analysis_imp_decl)
    transaction_type: str  # e.g. "WriteTransaction"
    role: str  # "actual" | "expected"
    agent_name: str  # for context / naming


class ScoreboardModel(BaseModel):
    """Model for scoreboard generation.

    Describes the scoreboard component: its name, the transaction type it
    operates on, the analysis export port names it exposes, and whether an
    internal predictor should be generated alongside it.
    """

    model_config = ConfigDict(frozen=True)

    name: NonEmptyStr
    exports: list[ScoreboardExport] = Field(default_factory=list)

    # Whether to generate an internal predictor alongside the scoreboard.
    has_predictor: bool = True
