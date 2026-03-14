"""Model for scoreboard generation."""

from pydantic import BaseModel, ConfigDict, Field

from uvm_pygen.models.utils.util_annotation import NonEmptyStr


class ScoreboardModel(BaseModel):
    """Model for scoreboard generation.

    Describes the scoreboard component: its name, the transaction type it
    operates on, the analysis export port names it exposes, and whether an
    internal predictor should be generated alongside it.
    """

    model_config = ConfigDict(frozen=True)

    name: NonEmptyStr
    transaction_type: NonEmptyStr

    # Names of the analysis export ports through which the scoreboard receives
    # transactions, e.g. ["item_collected_export", "expected_export"].
    analysis_exports: list[NonEmptyStr] = Field(default_factory=list)

    # Whether to generate an internal predictor alongside the scoreboard.
    has_predictor: bool = True
