"""
Backtest metrics — compute performance statistics from a completed run.

All metrics are computed from the trade ledger and equity curve.
Metrics are descriptive outputs of the engine. They are NOT used
to optimize or select strategies (that belongs to Prompt 05).

Metric definitions:
━━━━━━━━━━━━━━━━━━

win_rate         = winning_closed_trades / total_closed_trades
                   (0.0 if no closed trades)

gross_pnl        = sum(trade.gross_pnl) for all closed trades

net_pnl          = sum(trade.net_pnl) for all closed trades
                 = gross_pnl - total_fees - total_slippage - total_spread_cost

total_R          = sum(trade.r_multiple) for all trades with a known r_multiple
average_R        = total_R / len(trades with r_multiple)

max_drawdown     = min(equity_curve_point.drawdown) — most negative drawdown
                   Computed from equity curve, not from trades (no future leakage).

profit_factor    = sum(net_pnl of winning trades) / abs(sum(net_pnl of losing trades))
                   Undefined (inf) if no losing trades. 0 if no winning trades.

average_holding_duration = mean(trade.holding_duration_seconds) in seconds

IMPORTANT: These are engine validation metrics.
    Do NOT interpret them as evidence of future profitability.
    Do NOT use them to select strategies (Prompt 05).
    Do NOT present the ENGINE_VALIDATION_ONLY strategy results as research.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from crypto_research.core.domain import EquityCurvePoint, Trade


@dataclass
class BacktestMetrics:
    """
    Complete set of backtest performance metrics.

    All values computed from the trade ledger and equity curve.
    """

    # Trade counts
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float                # [0.0, 1.0]

    # PnL
    gross_pnl: float
    total_fees: float
    total_slippage_cost: float
    total_spread_cost: float
    net_pnl: float
    average_trade_net_pnl: float   # net_pnl / total_trades (0 if no trades)

    # R metrics
    total_R: Optional[float]       # None if no trades have risk_amount
    average_R: Optional[float]

    # Drawdown
    max_drawdown: float            # Most negative value (e.g. -0.05 = -5%)
    max_drawdown_pct: float        # Percentage version (e.g. -5.0)

    # Quality
    profit_factor: Optional[float] # None if no losing trades

    # Duration
    average_holding_duration_seconds: Optional[float]
    average_holding_duration: Optional[timedelta]

    # Capital
    initial_balance: float
    final_equity: float
    total_return_pct: float


def compute_metrics(
    trades: list[Trade],
    equity_curve: list[EquityCurvePoint],
    initial_balance: float,
) -> BacktestMetrics:
    """
    Compute all backtest metrics from the trade ledger and equity curve.

    Args:
        trades:          List of all completed Trade objects.
        equity_curve:    List of EquityCurvePoint snapshots.
        initial_balance: Starting capital (for return calculation).

    Returns:
        BacktestMetrics with all computed statistics.
    """
    total = len(trades)
    winners = [t for t in trades if t.net_pnl > 0]
    losers = [t for t in trades if t.net_pnl < 0]
    breakevens = [t for t in trades if t.net_pnl == 0]

    win_rate = len(winners) / total if total > 0 else 0.0

    gross_pnl = sum(t.gross_pnl for t in trades)
    total_fees = sum(t.fees for t in trades)
    total_slippage = sum(t.slippage_cost for t in trades)
    total_spread = sum(t.spread_cost for t in trades)
    net_pnl = sum(t.net_pnl for t in trades)
    avg_net_pnl = net_pnl / total if total > 0 else 0.0

    # R metrics
    r_trades = [t for t in trades if t.r_multiple is not None]
    total_R: Optional[float] = sum(t.r_multiple for t in r_trades) if r_trades else None
    avg_R: Optional[float] = (total_R / len(r_trades)) if r_trades else None

    # Drawdown
    if equity_curve:
        max_dd = min(p.drawdown for p in equity_curve)
    else:
        max_dd = 0.0
    max_dd_pct = max_dd * 100.0

    # Profit factor
    win_sum = sum(t.net_pnl for t in winners)
    loss_sum = abs(sum(t.net_pnl for t in losers))
    if loss_sum > 0:
        pf: Optional[float] = win_sum / loss_sum
    elif win_sum > 0:
        pf = float("inf")
    else:
        pf = None

    # Average holding duration
    durations = [t.holding_duration_seconds for t in trades if t.holding_duration_seconds is not None]
    avg_dur_sec: Optional[float] = sum(durations) / len(durations) if durations else None
    avg_dur: Optional[timedelta] = timedelta(seconds=avg_dur_sec) if avg_dur_sec is not None else None

    # Final equity
    final_equity = equity_curve[-1].equity if equity_curve else initial_balance
    total_return = (final_equity - initial_balance) / initial_balance * 100.0

    return BacktestMetrics(
        total_trades=total,
        winning_trades=len(winners),
        losing_trades=len(losers),
        breakeven_trades=len(breakevens),
        win_rate=win_rate,
        gross_pnl=gross_pnl,
        total_fees=total_fees,
        total_slippage_cost=total_slippage,
        total_spread_cost=total_spread,
        net_pnl=net_pnl,
        average_trade_net_pnl=avg_net_pnl,
        total_R=total_R,
        average_R=avg_R,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        profit_factor=pf,
        average_holding_duration_seconds=avg_dur_sec,
        average_holding_duration=avg_dur,
        initial_balance=initial_balance,
        final_equity=final_equity,
        total_return_pct=total_return,
    )
