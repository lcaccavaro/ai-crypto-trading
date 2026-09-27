"""
Regime Analyzer — Prompt 07.

Computes descriptive statistics (trade count, P&L, R, win rate, drawdown)
grouped by market regime.

Design:
    - Purely descriptive. No ranking. No causal claims.
    - Each regime group is independent.
    - Supports joining trades with regime labels by entry timestamp.

Limitations (disclosed per Prompt 07):
    - Trade entry timestamp is matched to regime at that exact candle.
    - Trades that span regime transitions are assigned to entry regime.
    - Regime definitions are deterministic but not ground truth.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from crypto_research.core.domain import Trade


@dataclass
class RegimeTradeStats:
    """Descriptive statistics for trades in a specific regime."""
    regime: str
    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    net_pnl: float
    total_R: Optional[float]
    avg_R: Optional[float]
    median_R: Optional[float]
    total_fees: float
    avg_holding_seconds: Optional[float]

    def to_dict(self) -> dict:
        return {
            "regime": self.regime,
            "trade_count": self.trade_count,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 4),
            "net_pnl": round(self.net_pnl, 4),
            "total_R": round(self.total_R, 4) if self.total_R is not None else None,
            "avg_R": round(self.avg_R, 4) if self.avg_R is not None else None,
            "median_R": round(self.median_R, 4) if self.median_R is not None else None,
            "total_fees": round(self.total_fees, 4),
            "avg_holding_seconds": round(self.avg_holding_seconds) if self.avg_holding_seconds else None,
        }


def assign_regimes_to_trades(
    trades: list[Trade],
    regime_lookup: dict[datetime, str],
) -> dict[str, Trade]:
    """
    Assign regime label to each trade based on entry timestamp.

    Args:
        trades: Completed trades from BacktestResult.
        regime_lookup: Dict mapping candle timestamp → regime label string.

    Returns:
        Dict mapping trade_id → regime_label (the label closest to and <= trade entry).
    """
    sorted_timestamps = sorted(regime_lookup.keys())
    result: dict[str, str] = {}

    for trade in trades:
        entry_ts = trade.entry_fill.timestamp if trade.entry_fill else None
        if entry_ts is None:
            result[trade.trade_id] = "UNKNOWN"
            continue

        # Find last regime timestamp <= entry_ts (PIT safe)
        regime = "UNKNOWN"
        for ts in sorted_timestamps:
            if ts <= entry_ts:
                regime = regime_lookup[ts]
            else:
                break
        result[trade.trade_id] = regime

    return result


def compute_regime_stats(
    trades: list[Trade],
    trade_regime_map: dict[str, str],
) -> list[RegimeTradeStats]:
    """
    Compute descriptive statistics grouped by regime.

    Args:
        trades: All completed trades.
        trade_regime_map: Mapping trade_id → regime_label.

    Returns:
        List of RegimeTradeStats, one per observed regime.
    """
    # Group trades by regime
    groups: dict[str, list[Trade]] = {}
    for trade in trades:
        regime = trade_regime_map.get(trade.trade_id, "UNKNOWN")
        groups.setdefault(regime, []).append(trade)

    stats_list = []
    for regime, group_trades in sorted(groups.items()):
        total = len(group_trades)
        winners = [t for t in group_trades if t.net_pnl > 0]
        losers = [t for t in group_trades if t.net_pnl < 0]

        r_values = [t.r_multiple for t in group_trades if t.r_multiple is not None]
        holding_durations = [t.holding_duration_seconds for t in group_trades if t.holding_duration_seconds]

        stats_list.append(RegimeTradeStats(
            regime=regime,
            trade_count=total,
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate=len(winners) / total if total > 0 else 0.0,
            net_pnl=sum(t.net_pnl for t in group_trades),
            total_R=sum(r_values) if r_values else None,
            avg_R=statistics.mean(r_values) if r_values else None,
            median_R=statistics.median(r_values) if r_values else None,
            total_fees=sum(t.fees for t in group_trades),
            avg_holding_seconds=statistics.mean(holding_durations) if holding_durations else None,
        ))

    return stats_list
