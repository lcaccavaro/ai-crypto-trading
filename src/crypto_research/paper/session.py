"""
Paper Trading Session — Prompt 08.

PaperTradingSession is the central state object for a paper trading session.
It does NOT contain execution logic — it holds:
    - Session identity (session_id, run_id)
    - Lifecycle state (INITIALIZING → RUNNING → STOPPING → STOPPED)
    - Accounting (balance, realized/unrealized P&L, equity)
    - Audit counters (signals, orders, fills, trades, errors)
    - Session metadata snapshot

Separation of concerns:
    PaperEngine drives the event loop.
    PaperTradingSession is the shared state object.
    PaperCheckpoint persists/restores it.
    PaperAuditWriter writes to CSV files.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import (
    ExecutionMode,
    PaperSessionState,
    Position,
    Trade,
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

# Termination reason codes
MANUAL_STOP = "MANUAL_STOP"
SCHEDULED_STOP = "SCHEDULED_STOP"
DATA_ERROR = "DATA_ERROR"
STATE_ERROR = "STATE_ERROR"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"


def _generate_session_id() -> str:
    now = datetime.now(timezone.utc)
    return f"PAPER_{now.strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}"


@dataclass
class PaperAccountingState:
    """Paper P&L and equity tracking."""

    initial_balance: float
    cash: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    gross_pnl: float = 0.0
    total_fees: float = 0.0
    total_slippage: float = 0.0
    total_spread: float = 0.0

    @property
    def net_pnl(self) -> float:
        return self.realized_pnl - self.total_fees - self.total_slippage - self.total_spread

    @property
    def equity(self) -> float:
        """cash + unrealized position value."""
        return self.cash + self.unrealized_pnl

    def to_dict(self) -> dict:
        return {
            "initial_balance": round(self.initial_balance, 4),
            "cash": round(self.cash, 4),
            "realized_pnl": round(self.realized_pnl, 4),
            "unrealized_pnl": round(self.unrealized_pnl, 4),
            "gross_pnl": round(self.gross_pnl, 4),
            "total_fees": round(self.total_fees, 4),
            "total_slippage": round(self.total_slippage, 4),
            "total_spread": round(self.total_spread, 4),
            "net_pnl": round(self.net_pnl, 4),
            "equity": round(self.equity, 4),
        }


@dataclass
class PaperCounters:
    """Event count audit trail."""

    market_events_received: int = 0
    market_events_rejected: int = 0
    market_events_duplicate: int = 0
    data_gaps: int = 0
    candles_processed: int = 0
    signals_generated: int = 0
    signals_accepted: int = 0
    signals_rejected: int = 0
    orders_created: int = 0
    fills_executed: int = 0
    positions_opened: int = 0
    positions_closed: int = 0
    trades_completed: int = 0
    wins: int = 0
    losses: int = 0
    checkpoints_saved: int = 0
    errors: int = 0
    warnings: int = 0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class PaperTradingSession:
    """
    Central state object for a paper trading session.

    Thread-safety note:
        This implementation is NOT thread-safe. The paper event loop must
        run in a single thread. If concurrency is needed in V2, add locks.
    """

    def __init__(
        self,
        config: ProjectConfiguration,
        run_id: str,
        session_id: str | None = None,
    ) -> None:
        self.session_id = session_id or _generate_session_id()
        self.run_id = run_id
        self._config = config
        self.execution_mode = ExecutionMode.PAPER

        # Lifecycle
        self.state: PaperSessionState = PaperSessionState.INITIALIZING
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.shutdown_reason: str | None = None

        # Accounting
        initial = config.paper_trading.initial_balance
        self.accounting = PaperAccountingState(
            initial_balance=initial,
            cash=initial,
        )

        # Counters
        self.counters = PaperCounters()

        # Open positions (position_id → Position)
        self.open_positions: dict[str, Position] = {}

        # Closed trades
        self.closed_trades: list[Trade] = []

        # State history for logging
        self._state_transitions: list[dict] = []

        logger.info(
            "Paper session created",
            session_id=self.session_id,
            run_id=self.run_id,
            initial_balance=initial,
            execution_mode=self.execution_mode.value,
        )

    # ─── Lifecycle ───────────────────────────────────────────────────────────────

    def transition_to(
        self, new_state: PaperSessionState, reason: str | None = None
    ) -> None:
        """Move session to a new state and log the transition."""
        old_state = self.state
        self.state = new_state
        ts = datetime.now(timezone.utc)
        self._state_transitions.append({
            "timestamp": ts.isoformat(),
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason or "",
        })
        logger.info(
            "Session state transition",
            session_id=self.session_id,
            from_state=old_state.value,
            to_state=new_state.value,
            reason=reason,
        )
        if new_state == PaperSessionState.RUNNING and self.start_time is None:
            self.start_time = ts
        if new_state in (PaperSessionState.STOPPED, PaperSessionState.FAILED):
            self.end_time = ts
            self.shutdown_reason = reason

    def start(self) -> None:
        self.transition_to(PaperSessionState.RUNNING, "Session started")

    def pause(self, reason: str) -> None:
        self.transition_to(PaperSessionState.PAUSED, reason)

    def resume(self) -> None:
        self.transition_to(PaperSessionState.RUNNING, "Resumed")

    def request_stop(self, reason: str = MANUAL_STOP) -> None:
        self.transition_to(PaperSessionState.STOPPING, reason)

    def mark_stopped(self) -> None:
        self.transition_to(PaperSessionState.STOPPED, "Session stopped cleanly")

    def mark_failed(self, reason: str) -> None:
        self.transition_to(PaperSessionState.FAILED, reason)
        self.counters.errors += 1

    def is_running(self) -> bool:
        return self.state == PaperSessionState.RUNNING

    def is_stopping_or_stopped(self) -> bool:
        return self.state in (
            PaperSessionState.STOPPING,
            PaperSessionState.STOPPED,
            PaperSessionState.FAILED,
        )

    # ─── Accounting ─────────────────────────────────────────────────────────────

    def record_trade_closed(self, trade: Trade) -> None:
        """Update accounting from a newly closed trade."""
        self.closed_trades.append(trade)
        self.accounting.realized_pnl += trade.net_pnl
        self.accounting.gross_pnl += trade.gross_pnl
        self.accounting.total_fees += trade.fees
        self.accounting.total_slippage += trade.slippage_cost
        self.accounting.total_spread += trade.spread_cost
        self.accounting.cash += trade.net_pnl
        self.counters.trades_completed += 1
        if trade.net_pnl > 0:
            self.counters.wins += 1
        else:
            self.counters.losses += 1

    def update_unrealized_pnl(self) -> None:
        """Recalculate unrealized P&L from all open positions."""
        self.accounting.unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.open_positions.values()
            if pos.unrealized_pnl is not None
        )

    def reconcile(self) -> dict[str, Any]:
        """
        Verify accounting integrity.

        Returns dict with reconciliation result and any discrepancies.
        """
        expected_equity = (
            self.accounting.initial_balance
            + self.accounting.realized_pnl
            - self.accounting.total_fees
            - self.accounting.total_slippage
            - self.accounting.total_spread
            + self.accounting.unrealized_pnl
        )
        actual_equity = self.accounting.equity
        discrepancy = abs(actual_equity - expected_equity)
        return {
            "expected_equity": round(expected_equity, 6),
            "actual_equity": round(actual_equity, 6),
            "discrepancy": round(discrepancy, 6),
            "reconciled": discrepancy < 0.01,  # 1 cent tolerance
        }

    # ─── Summary ────────────────────────────────────────────────────────────────

    def uptime_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()

    def to_metadata_dict(self) -> dict[str, Any]:
        """Return complete session metadata (for session_metadata.json)."""
        cfg = self._config
        return {
            "session_id": self.session_id,
            "run_id": self.run_id,
            "execution_mode": self.execution_mode.value,
            "state": self.state.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "shutdown_reason": self.shutdown_reason,
            "uptime_seconds": round(self.uptime_seconds(), 1),
            "market_type": cfg.data.market_type,
            "symbols": cfg.assets,
            "timeframes": cfg.timeframes,
            "initial_balance": cfg.paper_trading.initial_balance,
            "accounting": self.accounting.to_dict(),
            "counters": self.counters.to_dict(),
            "reconciliation": self.reconcile(),
            "state_transitions": self._state_transitions,
            "paper_label": "PAPER TRADING — SIMULATED EXECUTION — NO REAL ORDERS",
        }
