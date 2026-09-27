"""
Robustness Analyzer — Prompt 07.

Cross-asset, cross-timeframe, and leave-one-out (LOAO) analysis.

Design principles:
    - Descriptive only. No ranking. No best asset/timeframe.
    - Leave-one-out reveals concentration, not optimal subsets.
    - All results are computed from existing BacktestResult objects.
    - No BacktestEngine is instantiated here — computation is purely analytical.

Limitations (disclosed per Prompt 07):
    - Asset P&L contributions are summed across all trades for each asset.
    - Timeframe P&L contributions assume trades can be labelled by timeframe.
    - Leave-one-asset-out requires one result per asset available.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

from crypto_research.backtest.result import BacktestResult
from crypto_research.core.domain import Trade
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AssetRobustnessRecord:
    """Descriptive statistics for one asset."""
    asset: str
    trade_count: int
    net_pnl: float
    win_rate: float
    total_R: Optional[float]
    avg_R: Optional[float]
    pnl_share_pct: float  # share of total aggregate P&L

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "trade_count": self.trade_count,
            "net_pnl": round(self.net_pnl, 4),
            "win_rate": round(self.win_rate, 4),
            "total_R": round(self.total_R, 4) if self.total_R is not None else None,
            "avg_R": round(self.avg_R, 4) if self.avg_R is not None else None,
            "pnl_share_pct": round(self.pnl_share_pct, 2),
        }


@dataclass
class TimeframeRobustnessRecord:
    """Descriptive statistics for one timeframe."""
    timeframe: str
    trade_count: int
    net_pnl: float
    win_rate: float
    total_R: Optional[float]
    avg_R: Optional[float]
    pnl_share_pct: float

    def to_dict(self) -> dict:
        return {
            "timeframe": self.timeframe,
            "trade_count": self.trade_count,
            "net_pnl": round(self.net_pnl, 4),
            "win_rate": round(self.win_rate, 4),
            "total_R": round(self.total_R, 4) if self.total_R is not None else None,
            "avg_R": round(self.avg_R, 4) if self.avg_R is not None else None,
            "pnl_share_pct": round(self.pnl_share_pct, 2),
        }


@dataclass
class LeaveOneOutRecord:
    """Result of removing one asset from the aggregate."""
    excluded: str
    total_trades: int
    net_pnl: float
    net_pnl_change_vs_full: float   # signed difference vs full result
    net_pnl_change_pct: float       # % change vs full result

    def to_dict(self) -> dict:
        return {
            "excluded": self.excluded,
            "total_trades": self.total_trades,
            "net_pnl": round(self.net_pnl, 4),
            "net_pnl_change_vs_full": round(self.net_pnl_change_vs_full, 4),
            "net_pnl_change_pct": round(self.net_pnl_change_pct, 2),
        }


class RobustnessAnalyzer:
    """
    Computes cross-asset, cross-timeframe, and leave-one-out descriptive statistics.

    All inputs are BacktestResult objects from the existing engine.
    No engine is re-run here.
    """

    def analyze_by_asset(self, all_trades: list[Trade]) -> list[AssetRobustnessRecord]:
        """
        Group trades by asset and compute descriptive statistics per asset.

        Args:
            all_trades: All completed trades from a backtest run.

        Returns:
            List of AssetRobustnessRecord (one per asset observed).
        """
        # Group trades by asset
        asset_groups: dict[str, list[Trade]] = {}
        for trade in all_trades:
            asset_groups.setdefault(trade.asset, []).append(trade)

        total_pnl = sum(t.net_pnl for t in all_trades)
        records = []

        for asset, trades in sorted(asset_groups.items()):
            winners = [t for t in trades if t.net_pnl > 0]
            r_values = [t.r_multiple for t in trades if t.r_multiple is not None]
            net_pnl = sum(t.net_pnl for t in trades)
            share = (net_pnl / total_pnl * 100.0) if total_pnl != 0 else 0.0

            records.append(AssetRobustnessRecord(
                asset=asset,
                trade_count=len(trades),
                net_pnl=net_pnl,
                win_rate=len(winners) / len(trades) if trades else 0.0,
                total_R=sum(r_values) if r_values else None,
                avg_R=statistics.mean(r_values) if r_values else None,
                pnl_share_pct=share,
            ))

        logger.info(
            "Asset robustness analysis complete",
            assets=len(records),
            total_trades=len(all_trades),
        )
        return records

    def analyze_by_timeframe(self, all_trades: list[Trade]) -> list[TimeframeRobustnessRecord]:
        """
        Group trades by timeframe and compute descriptive statistics.

        Args:
            all_trades: All completed trades from a backtest run.

        Returns:
            List of TimeframeRobustnessRecord (one per timeframe observed).
        """
        tf_groups: dict[str, list[Trade]] = {}
        for trade in all_trades:
            tf_label = trade.timeframe.value if trade.timeframe else "UNKNOWN"
            tf_groups.setdefault(tf_label, []).append(trade)

        total_pnl = sum(t.net_pnl for t in all_trades)
        records = []

        for tf, trades in sorted(tf_groups.items()):
            winners = [t for t in trades if t.net_pnl > 0]
            r_values = [t.r_multiple for t in trades if t.r_multiple is not None]
            net_pnl = sum(t.net_pnl for t in trades)
            share = (net_pnl / total_pnl * 100.0) if total_pnl != 0 else 0.0

            records.append(TimeframeRobustnessRecord(
                timeframe=tf,
                trade_count=len(trades),
                net_pnl=net_pnl,
                win_rate=len(winners) / len(trades) if trades else 0.0,
                total_R=sum(r_values) if r_values else None,
                avg_R=statistics.mean(r_values) if r_values else None,
                pnl_share_pct=share,
            ))

        logger.info(
            "Timeframe robustness analysis complete",
            timeframes=len(records),
            total_trades=len(all_trades),
        )
        return records

    def leave_one_asset_out(
        self, all_trades: list[Trade], assets: list[str]
    ) -> list[LeaveOneOutRecord]:
        """
        For each asset, compute aggregate P&L with that asset excluded.

        Purpose: determine whether aggregate result depends disproportionately
        on one asset. This is descriptive research — not asset selection.

        Args:
            all_trades: All completed trades.
            assets:     List of all asset names in the portfolio.

        Returns:
            List of LeaveOneOutRecord (one per asset excluded).
        """
        full_pnl = sum(t.net_pnl for t in all_trades)
        records = []

        for excluded_asset in sorted(assets):
            subset = [t for t in all_trades if t.asset != excluded_asset]
            subset_pnl = sum(t.net_pnl for t in subset)
            delta = subset_pnl - full_pnl
            delta_pct = (delta / abs(full_pnl) * 100.0) if full_pnl != 0 else 0.0

            records.append(LeaveOneOutRecord(
                excluded=excluded_asset,
                total_trades=len(subset),
                net_pnl=subset_pnl,
                net_pnl_change_vs_full=delta,
                net_pnl_change_pct=delta_pct,
            ))

        logger.info(
            "Leave-one-asset-out analysis complete",
            assets_excluded=len(records),
        )
        return records

    def analyze_by_month(self, all_trades: list[Trade]) -> list[dict]:
        """
        Group trades by month for period dependency analysis.

        Returns list of dicts with period, trade_count, net_pnl, pnl_share_pct.
        """
        month_groups: dict[str, list[Trade]] = {}
        for trade in all_trades:
            entry_ts = trade.entry_fill.timestamp if trade.entry_fill else None
            if entry_ts:
                period = entry_ts.strftime("%Y-%m")
                month_groups.setdefault(period, []).append(trade)

        total_pnl = sum(t.net_pnl for t in all_trades)
        result = []
        for period, trades in sorted(month_groups.items()):
            net_pnl = sum(t.net_pnl for t in trades)
            result.append({
                "period": period,
                "trade_count": len(trades),
                "net_pnl": round(net_pnl, 4),
                "pnl_share_pct": round(net_pnl / total_pnl * 100.0, 2) if total_pnl != 0 else 0.0,
            })
        return result
