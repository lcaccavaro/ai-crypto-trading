"""
Portfolio Result Writer.

Coordinates writing all Prompt 05 specific ledgers to disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from crypto_research.portfolio.decision_ledger import DecisionLedger
from crypto_research.portfolio.strategy_state_ledger import StrategyStateLedger
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PortfolioResultWriter:
    """Exports portfolio orchestration ledgers and metadata to disk."""

    def __init__(self, run_directory: str | Path):
        self.output_dir = Path(run_directory)

    def write_all(
        self,
        decision_ledger: DecisionLedger,
        state_ledger: StrategyStateLedger,
        portfolio_state_records: list[dict], # if we decide to export it
        opportunity_scores: list[dict],      # if we decide to export it
        metadata: dict,
    ) -> None:
        """Write all Prompt 05 outputs."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Ledgers
        decision_ledger.to_csv(self.output_dir / "risk_decisions.csv")
        state_ledger.to_csv(self.output_dir / "strategy_state_history.csv")
        
        # Metadata
        meta_path = self.output_dir / "portfolio_metadata.json"
        with meta_path.open("w") as f:
            json.dump(metadata, f, indent=2)
            
        # Additional files can be written here (e.g. opportunity scores directly from ledger if we had one)
        logger.info(f"Portfolio results written to {self.output_dir}")
