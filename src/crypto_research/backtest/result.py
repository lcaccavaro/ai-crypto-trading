"""
Backtest result container and persistence.

BacktestResult:
    Complete immutable result of a backtest run.
    Contains all trades, orders, fills, equity curve, events, and metrics.

BacktestResultWriter:
    Writes all result artifacts to disk under results/backtests/<run_id>/.

Output files:
    run_metadata.json        — Run ID, timestamp, config snapshot
    config_snapshot.yaml     — Full config used for this run
    trades.csv               — All completed trades
    orders.csv               — All orders (accepted + rejected)
    fills.csv                — All fills (entry + exit)
    equity_curve.csv         — Timestamped equity curve
    execution_events.csv     — Full execution event ledger
    metrics.json             — Computed performance metrics
    summary.json             — Human-readable summary
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from crypto_research.backtest.metrics import BacktestMetrics, compute_metrics
from crypto_research.core.domain import (
    EquityCurvePoint,
    ExecutionEvent,
    Fill,
    Order,
    Position,
    Trade,
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False


@dataclass
class BacktestResult:
    """
    Complete result of a backtest run.

    All lists are immutable snapshots captured at run completion.
    This object is the canonical output of BacktestEngine.run().

    Fields:
        run_id:          Unique run identifier.
        strategy_name:   Name of the strategy that was run.
        start_date:      Backtest start date string.
        end_date:        Backtest end date string.
        symbols:         Symbols included in this run.
        timeframes:      Timeframes used.
        completed_at:    UTC timestamp when the run completed.
        trades:          All completed trades.
        open_positions:  Positions still open at end of simulation.
        orders:          All orders (filled, rejected, cancelled).
        fills:           All fills (entry and exit).
        equity_curve:    Equity curve snapshots.
        events:          Full execution event ledger.
        metrics:         Computed performance metrics.
        config_snapshot: Full config used for this run.
    """

    run_id: str
    strategy_name: str
    start_date: str
    end_date: str
    symbols: list[str]
    timeframes: list[str]
    completed_at: datetime
    trades: list[Trade]
    open_positions: list[Position]
    orders: list[Order]
    fills: list[Fill]
    equity_curve: list[EquityCurvePoint]
    events: list[ExecutionEvent]
    metrics: BacktestMetrics
    config_snapshot: dict[str, Any]

    @classmethod
    def build(
        cls,
        run_id: str,
        strategy_name: str,
        start_date: str,
        end_date: str,
        symbols: list[str],
        timeframes: list[str],
        trades: list[Trade],
        open_positions: list[Position],
        orders: list[Order],
        fills: list[Fill],
        equity_curve: list[EquityCurvePoint],
        events: list[ExecutionEvent],
        initial_balance: float,
        config_snapshot: dict[str, Any],
    ) -> "BacktestResult":
        """
        Build a BacktestResult, computing metrics automatically.

        Args:
            run_id:           Unique run identifier.
            strategy_name:    Strategy name.
            start_date:       Backtest start date.
            end_date:         Backtest end date.
            symbols:          Symbols included.
            timeframes:       Timeframes used.
            trades:           Completed trades.
            open_positions:   Positions still open at end.
            orders:           All orders.
            fills:            All fills.
            equity_curve:     Equity curve points.
            events:           Execution events.
            initial_balance:  Starting capital for metrics.
            config_snapshot:  Config used for this run.

        Returns:
            BacktestResult with computed metrics.
        """
        metrics = compute_metrics(trades, equity_curve, initial_balance)
        return cls(
            run_id=run_id,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            timeframes=timeframes,
            completed_at=datetime.now(timezone.utc),
            trades=trades,
            open_positions=open_positions,
            orders=orders,
            fills=fills,
            equity_curve=equity_curve,
            events=events,
            metrics=metrics,
            config_snapshot=config_snapshot,
        )


class BacktestResultWriter:
    """
    Writes backtest results to disk under results/backtests/<run_id>/.

    All files are written atomically — a partial write is detectable
    because metrics.json and summary.json are written last.
    """

    def __init__(self, base_dir: str | Path = "results/backtests") -> None:
        self._base_dir = Path(base_dir)

    def write(self, result: BacktestResult) -> Path:
        """
        Write all result artifacts to disk.

        Args:
            result: BacktestResult to persist.

        Returns:
            Path to the run output directory.
        """
        run_dir = self._base_dir / result.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Writing backtest results", run_id=result.run_id, path=str(run_dir))

        # Write in dependency order — metadata first, summary last
        self._write_run_metadata(result, run_dir)
        self._write_config_snapshot(result, run_dir)
        self._write_trades(result, run_dir)
        self._write_orders(result, run_dir)
        self._write_fills(result, run_dir)
        self._write_equity_curve(result, run_dir)
        self._write_events(result, run_dir)
        self._write_metrics(result, run_dir)
        self._write_summary(result, run_dir)

        logger.info(
            "Backtest results written",
            run_id=result.run_id,
            trades=len(result.trades),
            files=9,
        )
        return run_dir

    def _write_run_metadata(self, result: BacktestResult, run_dir: Path) -> None:
        metadata = {
            "run_id": result.run_id,
            "strategy_name": result.strategy_name,
            "completed_at": result.completed_at.isoformat(),
            "start_date": result.start_date,
            "end_date": result.end_date,
            "symbols": result.symbols,
            "timeframes": result.timeframes,
            "total_trades": len(result.trades),
            "open_positions_at_end": len(result.open_positions),
        }
        with open(run_dir / "run_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def _write_config_snapshot(self, result: BacktestResult, run_dir: Path) -> None:
        with open(run_dir / "config_snapshot.yaml", "w") as f:
            yaml.dump(result.config_snapshot, f, default_flow_style=False)

    def _write_trades(self, result: BacktestResult, run_dir: Path) -> None:
        if not _PANDAS_AVAILABLE:
            # Fallback: write JSON lines
            with open(run_dir / "trades.csv", "w") as f:
                f.write("trade_id,asset,side,entry_price,exit_price,quantity,net_pnl,r_multiple,exit_reason\n")
                for t in result.trades:
                    f.write(
                        f"{t.trade_id},{t.asset},{t.side.value},"
                        f"{t.entry_fill.fill_price},{t.exit_fill.fill_price},"
                        f"{t.entry_fill.quantity},{t.net_pnl},{t.r_multiple},{t.exit_reason}\n"
                    )
            return

        rows = []
        for t in result.trades:
            rows.append({
                "trade_id": t.trade_id,
                "asset": t.asset,
                "side": t.side.value,
                "entry_time": t.entry_fill.timestamp.isoformat(),
                "exit_time": t.exit_fill.timestamp.isoformat(),
                "entry_price": t.entry_fill.fill_price,
                "exit_price": t.exit_fill.fill_price,
                "quantity": t.entry_fill.quantity,
                "gross_pnl": t.gross_pnl,
                "fees": t.fees,
                "slippage_cost": t.slippage_cost,
                "spread_cost": t.spread_cost,
                "net_pnl": t.net_pnl,
                "r_multiple": t.r_multiple,
                "risk_amount": t.risk_amount,
                "exit_reason": t.exit_reason,
                "initial_stop": t.initial_stop,
                "target_price": t.target_price,
                "holding_duration_seconds": t.holding_duration_seconds,
                "strategy_name": t.strategy_name,
            })
        pd.DataFrame(rows).to_csv(run_dir / "trades.csv", index=False)

    def _write_orders(self, result: BacktestResult, run_dir: Path) -> None:
        if not _PANDAS_AVAILABLE:
            with open(run_dir / "orders.csv", "w") as f:
                f.write("order_id,asset,side,status,rejection_reason,timestamp\n")
                for o in result.orders:
                    f.write(
                        f"{o.order_id},{o.asset},{o.side.value},"
                        f"{o.status.value},{o.rejection_reason},{o.timestamp.isoformat()}\n"
                    )
            return

        rows = []
        for o in result.orders:
            rows.append({
                "order_id": o.order_id,
                "timestamp": o.timestamp.isoformat(),
                "asset": o.asset,
                "side": o.side.value,
                "order_type": o.order_type.value,
                "quantity": o.quantity,
                "price": o.price,
                "stop_price": o.stop_price,
                "target_price": o.target_price,
                "status": o.status.value,
                "rejection_reason": o.rejection_reason.value if o.rejection_reason else None,
                "strategy_name": o.strategy_name,
            })
        pd.DataFrame(rows).to_csv(run_dir / "orders.csv", index=False)

    def _write_fills(self, result: BacktestResult, run_dir: Path) -> None:
        if not _PANDAS_AVAILABLE:
            with open(run_dir / "fills.csv", "w") as f:
                f.write("fill_id,order_id,asset,side,fill_price,quantity,fees\n")
                for fi in result.fills:
                    f.write(
                        f"{fi.fill_id},{fi.order_id},{fi.asset},{fi.side.value},"
                        f"{fi.fill_price},{fi.quantity},{fi.fees}\n"
                    )
            return

        rows = []
        for fi in result.fills:
            rows.append({
                "fill_id": fi.fill_id,
                "order_id": fi.order_id,
                "timestamp": fi.timestamp.isoformat(),
                "asset": fi.asset,
                "side": fi.side.value,
                "fill_price": fi.fill_price,
                "quantity": fi.quantity,
                "fees": fi.fees,
                "slippage": fi.slippage,
                "spread_cost": fi.spread_cost,
            })
        pd.DataFrame(rows).to_csv(run_dir / "fills.csv", index=False)

    def _write_equity_curve(self, result: BacktestResult, run_dir: Path) -> None:
        if not _PANDAS_AVAILABLE:
            with open(run_dir / "equity_curve.csv", "w") as f:
                f.write("timestamp,equity,cash,drawdown,realized_pnl\n")
                for p in result.equity_curve:
                    f.write(
                        f"{p.timestamp.isoformat()},{p.equity},{p.cash},"
                        f"{p.drawdown},{p.realized_pnl}\n"
                    )
            return

        rows = []
        for p in result.equity_curve:
            rows.append({
                "timestamp": p.timestamp.isoformat(),
                "equity": p.equity,
                "cash": p.cash,
                "realized_pnl": p.realized_pnl,
                "unrealized_pnl": p.unrealized_pnl,
                "gross_exposure": p.gross_exposure,
                "net_exposure": p.net_exposure,
                "drawdown": p.drawdown,
            })
        pd.DataFrame(rows).to_csv(run_dir / "equity_curve.csv", index=False)

    def _write_events(self, result: BacktestResult, run_dir: Path) -> None:
        if not _PANDAS_AVAILABLE:
            with open(run_dir / "execution_events.csv", "w") as f:
                f.write("event_id,timestamp,event_type,asset\n")
                for e in result.events:
                    f.write(f"{e.event_id},{e.timestamp.isoformat()},{e.event_type.value},{e.asset}\n")
            return

        rows = []
        for e in result.events:
            rows.append({
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type.value,
                "run_id": e.run_id,
                "asset": e.asset,
                "order_id": e.order_id,
                "position_id": e.position_id,
                "trade_id": e.trade_id,
            })
        pd.DataFrame(rows).to_csv(run_dir / "execution_events.csv", index=False)

    def _write_metrics(self, result: BacktestResult, run_dir: Path) -> None:
        m = result.metrics
        metrics_dict = {
            "total_trades": m.total_trades,
            "winning_trades": m.winning_trades,
            "losing_trades": m.losing_trades,
            "breakeven_trades": m.breakeven_trades,
            "win_rate": m.win_rate,
            "gross_pnl": m.gross_pnl,
            "total_fees": m.total_fees,
            "total_slippage_cost": m.total_slippage_cost,
            "total_spread_cost": m.total_spread_cost,
            "net_pnl": m.net_pnl,
            "average_trade_net_pnl": m.average_trade_net_pnl,
            "total_R": m.total_R,
            "average_R": m.average_R,
            "max_drawdown": m.max_drawdown,
            "max_drawdown_pct": m.max_drawdown_pct,
            "profit_factor": m.profit_factor if m.profit_factor != float("inf") else None,
            "average_holding_duration_seconds": m.average_holding_duration_seconds,
            "initial_balance": m.initial_balance,
            "final_equity": m.final_equity,
            "total_return_pct": m.total_return_pct,
        }
        with open(run_dir / "metrics.json", "w") as f:
            json.dump(metrics_dict, f, indent=2)

    def _write_summary(self, result: BacktestResult, run_dir: Path) -> None:
        m = result.metrics
        summary = {
            "run_id": result.run_id,
            "strategy": result.strategy_name,
            "period": f"{result.start_date} to {result.end_date}",
            "symbols": result.symbols,
            "WARNING": (
                "ENGINE_VALIDATION_ONLY strategy results. "
                "DO NOT interpret as research findings or evidence of edge."
            ),
            "initial_balance_usdt": m.initial_balance,
            "final_equity_usdt": round(m.final_equity, 2),
            "net_pnl_usdt": round(m.net_pnl, 2),
            "total_return_pct": round(m.total_return_pct, 4),
            "total_trades": m.total_trades,
            "win_rate_pct": round(m.win_rate * 100, 2),
            "max_drawdown_pct": round(m.max_drawdown_pct, 4),
            "profit_factor": m.profit_factor if m.profit_factor != float("inf") else "inf",
            "average_R": round(m.average_R, 4) if m.average_R is not None else None,
        }
        with open(run_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
