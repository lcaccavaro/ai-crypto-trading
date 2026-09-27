"""
Decision Ledger.

An append-only ledger that records every risk orchestration decision for strategy signals.
"""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_research.core.domain import RiskDecisionRecord
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class DecisionLedger:
    """
    Append-only ledger for portfolio risk decisions on strategy signals.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._records: list[RiskDecisionRecord] = []

    def record(self, decision: RiskDecisionRecord) -> None:
        """Record a risk decision."""
        self._records.append(decision)

    def to_csv(self, path: str | Path) -> Path:
        """Export ledger to CSV."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self._records:
            logger.warning("Decision ledger is empty. Generating empty CSV.")
            path.write_text(
                "timestamp,run_id,strategy_id,strategy_version,instance_id,symbol,timeframe,"
                "signal,score,score_version,risk_budget,approved_quantity,portfolio_equity,"
                "daily_return_pct,consecutive_losses,strategy_state,decision,primary_reason,"
                "rejection_reasons\n"
            )
            return path

        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "run_id",
                "strategy_id",
                "strategy_version",
                "instance_id",
                "symbol",
                "timeframe",
                "signal",
                "score",
                "score_version",
                "risk_budget",
                "approved_quantity",
                "portfolio_equity",
                "daily_return_pct",
                "consecutive_losses",
                "strategy_state",
                "decision",
                "primary_reason",
                "rejection_reasons",
            ])
            for rec in self._records:
                writer.writerow([
                    rec.timestamp.isoformat(),
                    rec.run_id,
                    rec.strategy_id,
                    rec.strategy_version,
                    rec.instance_id,
                    rec.symbol,
                    rec.timeframe.value if rec.timeframe else "",
                    rec.signal.value,
                    round(rec.score, 4) if rec.score is not None else "",
                    rec.score_version or "",
                    round(rec.risk_budget, 4) if rec.risk_budget is not None else "",
                    round(rec.approved_quantity, 6) if rec.approved_quantity is not None else "",
                    round(rec.portfolio_equity, 2),
                    round(rec.daily_return_pct, 4),
                    rec.consecutive_losses,
                    rec.strategy_state.value,
                    rec.decision.value,
                    rec.primary_reason,
                    "|".join(r.value for r in rec.rejection_reasons),
                ])
        
        logger.info(f"Exported {len(self._records)} risk decisions to {path.name}")
        return path

    def records(self) -> list[RiskDecisionRecord]:
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)
