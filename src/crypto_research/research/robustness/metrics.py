"""
Robustness Stability Metrics — Prompt 07.

Computes temporal stability statistics from a series of OOS window results.
These metrics describe how consistent OOS performance is across time,
NOT what future performance will be.

No optimization is performed here.
No strategy ranking is produced.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

from crypto_research.research.walk_forward.runner import WindowResult


@dataclass
class OOSStabilityMetrics:
    """
    Statistics across all valid OOS windows.

    Used to assess consistency of OOS performance — not to optimize.
    """

    total_windows: int
    valid_windows: int       # windows where OOS ran without error
    positive_oos_windows: int
    negative_oos_windows: int
    pct_positive_windows: float

    # OOS P&L distribution
    median_oos_net_pnl: Optional[float]
    mean_oos_net_pnl: Optional[float]
    stdev_oos_net_pnl: Optional[float]
    min_oos_net_pnl: Optional[float]       # worst window
    max_oos_net_pnl: Optional[float]       # best window
    total_oos_net_pnl: Optional[float]     # non-overlapping aggregate

    # OOS R distribution
    median_oos_avg_R: Optional[float]
    mean_oos_avg_R: Optional[float]

    # Trade count
    total_oos_trades: int
    median_oos_trades_per_window: Optional[float]

    # OOS drawdown
    median_oos_max_drawdown: Optional[float]
    worst_oos_max_drawdown: Optional[float]

    def to_dict(self) -> dict:
        return {
            "total_windows": self.total_windows,
            "valid_windows": self.valid_windows,
            "positive_oos_windows": self.positive_oos_windows,
            "pct_positive_windows": round(self.pct_positive_windows, 4),
            "median_oos_net_pnl": self._r(self.median_oos_net_pnl),
            "mean_oos_net_pnl": self._r(self.mean_oos_net_pnl),
            "stdev_oos_net_pnl": self._r(self.stdev_oos_net_pnl),
            "min_oos_net_pnl": self._r(self.min_oos_net_pnl),
            "max_oos_net_pnl": self._r(self.max_oos_net_pnl),
            "total_oos_net_pnl": self._r(self.total_oos_net_pnl),
            "median_oos_avg_R": self._r(self.median_oos_avg_R),
            "mean_oos_avg_R": self._r(self.mean_oos_avg_R),
            "total_oos_trades": self.total_oos_trades,
            "median_oos_trades_per_window": self._r(self.median_oos_trades_per_window),
            "median_oos_max_drawdown": self._r(self.median_oos_max_drawdown),
            "worst_oos_max_drawdown": self._r(self.worst_oos_max_drawdown),
        }

    @staticmethod
    def _r(v: Optional[float]) -> Optional[float]:
        return round(v, 6) if v is not None else None


def compute_oos_stability(window_results: list[WindowResult]) -> OOSStabilityMetrics:
    """
    Compute stability metrics from a list of WindowResult objects.

    Only windows with a successful OOS run (oos_result is not None) contribute.
    Windows with oos_error are counted in `total_windows` but excluded from metrics.
    """
    total = len(window_results)
    valid = [wr for wr in window_results if wr.oos_result is not None]
    valid_count = len(valid)

    if not valid:
        return OOSStabilityMetrics(
            total_windows=total,
            valid_windows=0,
            positive_oos_windows=0,
            negative_oos_windows=0,
            pct_positive_windows=0.0,
            median_oos_net_pnl=None,
            mean_oos_net_pnl=None,
            stdev_oos_net_pnl=None,
            min_oos_net_pnl=None,
            max_oos_net_pnl=None,
            total_oos_net_pnl=None,
            median_oos_avg_R=None,
            mean_oos_avg_R=None,
            total_oos_trades=0,
            median_oos_trades_per_window=None,
            median_oos_max_drawdown=None,
            worst_oos_max_drawdown=None,
        )

    pnls = [wr.oos_result.metrics.net_pnl for wr in valid]
    positive_wins = sum(1 for p in pnls if p > 0)
    negative_wins = sum(1 for p in pnls if p < 0)

    avg_R_list = [wr.oos_result.metrics.average_R for wr in valid if wr.oos_result.metrics.average_R is not None]
    trade_counts = [wr.oos_result.metrics.total_trades for wr in valid]
    drawdowns = [wr.oos_result.metrics.max_drawdown for wr in valid]

    return OOSStabilityMetrics(
        total_windows=total,
        valid_windows=valid_count,
        positive_oos_windows=positive_wins,
        negative_oos_windows=negative_wins,
        pct_positive_windows=positive_wins / valid_count if valid_count > 0 else 0.0,
        median_oos_net_pnl=statistics.median(pnls) if pnls else None,
        mean_oos_net_pnl=statistics.mean(pnls) if pnls else None,
        stdev_oos_net_pnl=statistics.stdev(pnls) if len(pnls) > 1 else None,
        min_oos_net_pnl=min(pnls) if pnls else None,
        max_oos_net_pnl=max(pnls) if pnls else None,
        total_oos_net_pnl=sum(pnls) if pnls else None,
        median_oos_avg_R=statistics.median(avg_R_list) if avg_R_list else None,
        mean_oos_avg_R=statistics.mean(avg_R_list) if avg_R_list else None,
        total_oos_trades=sum(trade_counts),
        median_oos_trades_per_window=statistics.median(trade_counts) if trade_counts else None,
        median_oos_max_drawdown=statistics.median(drawdowns) if drawdowns else None,
        worst_oos_max_drawdown=min(drawdowns) if drawdowns else None,
    )
