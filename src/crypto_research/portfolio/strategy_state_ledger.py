"""
Strategy State Ledger.

An append-only ledger that records every state transition of a strategy.
"""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_research.core.domain import StrategyState
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class StrategyStateLedger:
    """
    Append-only ledger for strategy state transitions.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._records: list[StrategyState] = []

    def record(self, state: StrategyState) -> None:
        """Record a state transition."""
        self._records.append(state)

    def to_csv(self, path: str | Path) -> Path:
        """Export ledger to CSV."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self._records:
            logger.warning("Strategy state ledger is empty. Generating empty CSV.")
            path.write_text(
                "timestamp,strategy_id,instance_id,state,reason,consecutive_losses,last_trade_result,cooldown_start,cooldown_until\n"
            )
            return path

        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "strategy_id",
                "instance_id",
                "state",
                "reason",
                "consecutive_losses",
                "last_trade_result",
                "cooldown_start",
                "cooldown_until",
            ])
            for rec in self._records:
                writer.writerow([
                    rec.timestamp.isoformat(),
                    rec.strategy_id,
                    rec.instance_id,
                    rec.state.value,
                    rec.reason,
                    rec.consecutive_losses,
                    rec.last_trade_result or "",
                    rec.cooldown_start.isoformat() if rec.cooldown_start else "",
                    rec.cooldown_until.isoformat() if rec.cooldown_until else "",
                ])
        
        logger.info(f"Exported {len(self._records)} state transitions to {path.name}")
        return path

    def records(self) -> list[StrategyState]:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)
