from dataclasses import dataclass

@dataclass
class ScoreboardModel:
    """Model pre generovanie scoreboardu."""
    name: str
    transaction_type: str
    analysis_exports: list[str] # Názvy portov, cez ktoré SB prijíma transakcie (napr. "item_collected_export")
    has_predictor: bool = True # Či chceme generovať aj interný predictor