"""
Paper Trading Audit Writer — Prompt 08.

Writes all session audit CSV files to results/paper/<session_id>/.

Files written:
    market_events.csv
    signals.csv
    opportunity_scores.csv
    risk_decisions.csv
    orders.csv
    fills.csv
    positions.csv
    trades.csv
    strategy_state_history.csv
    portfolio_state.csv
    session_metadata.json
    config_snapshot.yaml

Design:
    - Append-only writes (header written once on first call per file).
    - One CSV row per event — never batch-overwrites.
    - No event may be silently dropped.
"""

from __future__ import annotations

import csv
import json
import yaml
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from crypto_research.core.domain import (
    Candle,
    ExecutionMode,
    Fill,
    Order,
    PaperAuditEventType,
    Position,
    Trade,
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PaperAuditWriter:
    """
    Append-only CSV writer for paper session events.

    Creates the session directory and all files on first write.
    """

    def __init__(self, session_dir: str | Path, session_id: str) -> None:
        self._dir = Path(session_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._session_id = session_id

        # Track which files have been initialized (header written)
        self._initialized: set[str] = set()

    # ─── Writers ────────────────────────────────────────────────────────────────

    def write_market_event(
        self, event_type: PaperAuditEventType, candle: Candle | None = None,
        symbol: str = "", timeframe: str = "", detail: str = ""
    ) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "event_type": event_type.value,
            "symbol": symbol or (candle.symbol if candle else ""),
            "timeframe": timeframe or (candle.timeframe.value if candle else ""),
            "candle_ts": candle.timestamp.isoformat() if candle else "",
            "open": candle.open if candle else "",
            "high": candle.high if candle else "",
            "low": candle.low if candle else "",
            "close": candle.close if candle else "",
            "volume": candle.volume if candle else "",
            "detail": detail,
        }
        self._append("market_events.csv", row)

    def write_signal(self, signal, score: float | None = None) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "signal_id": getattr(signal, "signal_id", ""),
            "strategy_id": getattr(signal, "strategy_id", ""),
            "symbol": getattr(signal, "asset", ""),
            "timeframe": getattr(signal, "timeframe", ""),
            "direction": getattr(signal, "direction", ""),
            "strength": getattr(signal, "strength", ""),
            "stop_distance": getattr(signal, "stop_distance_pct", ""),
            "score": round(score, 4) if score is not None else "",
            "execution_mode": ExecutionMode.PAPER.value,
        }
        self._append("signals.csv", row)

    def write_risk_decision(self, decision) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "signal_id": getattr(decision, "signal_id", ""),
            "strategy_id": getattr(decision, "strategy_id", ""),
            "symbol": getattr(decision, "symbol", ""),
            "outcome": getattr(decision, "outcome", ""),
            "rejection_reason": getattr(decision, "rejection_reason", ""),
            "score": getattr(decision, "score", ""),
            "execution_mode": ExecutionMode.PAPER.value,
        }
        self._append("risk_decisions.csv", row)

    def write_order(self, order: Order) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "order_id": order.order_id,
            "asset": order.asset,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "price": order.price or "",
            "stop_price": order.stop_price or "",
            "target_price": order.target_price or "",
            "status": order.status.value,
            "strategy_name": order.strategy_name,
            "execution_mode": ExecutionMode.PAPER.value,
        }
        self._append("orders.csv", row)

    def write_fill(self, fill: Fill) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "fill_id": fill.fill_id,
            "order_id": fill.order_id,
            "asset": fill.asset,
            "side": fill.side.value,
            "quantity": fill.quantity,
            "fill_price": fill.fill_price,
            "fees": fill.fees,
            "slippage": fill.slippage,
            "spread_cost": fill.spread_cost,
            "execution_mode": ExecutionMode.PAPER.value,
        }
        self._append("fills.csv", row)

    def write_trade(self, trade: Trade) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "trade_id": trade.trade_id,
            "asset": trade.asset,
            "side": trade.side.value if trade.side else "",
            "strategy_name": trade.strategy_name,
            "entry_price": trade.entry_fill.fill_price,
            "exit_price": trade.exit_fill.fill_price,
            "initial_stop": trade.initial_stop or "",
            "target_price": trade.target_price or "",
            "quantity": trade.entry_fill.quantity,
            "gross_pnl": round(trade.gross_pnl, 4),
            "fees": round(trade.fees, 4),
            "slippage_cost": round(trade.slippage_cost, 4),
            "spread_cost": round(trade.spread_cost, 4),
            "net_pnl": round(trade.net_pnl, 4),
            "r_multiple": round(trade.r_multiple, 4) if trade.r_multiple is not None else "",
            "exit_reason": trade.exit_reason,
            "holding_duration_seconds": trade.holding_duration_seconds or "",
            "execution_mode": ExecutionMode.PAPER.value,
            "paper_label": "PAPER TRADING — SIMULATED — NO REAL ORDERS",
        }
        self._append("trades.csv", row)

    def write_position_snapshot(self, position: Position, event: str) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self._session_id,
            "event": event,
            "position_id": position.position_id,
            "asset": position.asset,
            "side": position.side.value,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "current_price": position.current_price or "",
            "unrealized_pnl": position.unrealized_pnl if position.unrealized_pnl is not None else "",
            "stop_price": position.stop_price or "",
            "target_price": position.target_price or "",
            "execution_mode": ExecutionMode.PAPER.value,
        }
        self._append("positions.csv", row)

    def write_portfolio_state(self, state_dict: dict) -> None:
        state_dict["session_id"] = self._session_id
        state_dict["execution_mode"] = ExecutionMode.PAPER.value
        self._append("portfolio_state.csv", state_dict)

    def write_heartbeat(self, payload: dict) -> None:
        payload["session_id"] = self._session_id
        self._append("heartbeats.csv", payload)

    def write_session_metadata(self, metadata: dict) -> None:
        path = self._dir / "session_metadata.json"
        with open(path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info("Session metadata written", path=str(path))

    def write_config_snapshot(self, config_yaml: str) -> None:
        path = self._dir / "config_snapshot.yaml"
        path.write_text(config_yaml)

    # ─── Internal ────────────────────────────────────────────────────────────────

    def _append(self, filename: str, row: dict) -> None:
        path = self._dir / filename
        write_header = filename not in self._initialized

        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()), extrasaction="ignore")
            if write_header:
                writer.writeheader()
                self._initialized.add(filename)
            writer.writerow(row)
