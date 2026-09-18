"""
Execution engine interface for the crypto research laboratory.

Defines the Protocol for order submission and position management.
Prompt 03 will implement the candle-by-candle backtesting execution engine.

Design principle:
    The execution interface is intentionally identical for both backtesting
    and future paper trading (Prompt 08). The data source changes, but the
    order lifecycle (Order → Fill → Position → Trade) remains the same.

Execution flow:
    Strategy generates Signal
        ↓
    Risk Manager evaluates Signal → RiskDecision
        ↓ (if approved)
    Research Orchestrator creates Order
        ↓
    ExecutionEngine.submit_order(order) → Fill
        ↓
    Position opened/updated
        ↓
    Position closed → Trade recorded
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from crypto_research.core.domain import Fill, Order, Position, Trade


@runtime_checkable
class ExecutionEngine(Protocol):
    """
    Contract for order submission and position lifecycle management.

    Prompt 03 will implement BacktestExecutionEngine using this interface.
    Prompt 08 will implement PaperTradingExecutionEngine using this interface.

    Both implementations share the same domain objects (Order, Fill,
    Position, Trade), ensuring that strategy logic is reusable in both modes.
    """

    @property
    def run_id(self) -> str:
        """Research run ID associated with this execution engine instance."""
        ...

    def submit_order(self, order: Order) -> Fill:
        """
        Submit an order and return the resulting fill.

        In backtest mode: simulates fill based on historical candle data.
        In paper-trading mode: submits to exchange API and returns fill.

        Args:
            order: A fully constructed Order object.

        Returns:
            A Fill representing the executed order.

        Raises:
            ExecutionError: If the order is invalid or cannot be executed.
            ExecutionError: If fill simulation produces unrealistic results.
        """
        ...

    def close_position(self, position: Position, reason: str) -> Trade:
        """
        Close an open position and return the completed Trade record.

        Args:
            position:   The open position to close.
            reason:     Exit reason for the trade journal
                        (e.g. 'target', 'stop', 'time_exit', 'daily_stop').

        Returns:
            A Trade representing the complete round-trip.

        Raises:
            ExecutionError: If the position cannot be found or closed.
        """
        ...

    def get_open_positions(self) -> list[Position]:
        """Return all currently open positions managed by this engine."""
        ...

    def get_closed_trades(self) -> list[Trade]:
        """Return all completed trades in this research run."""
        ...

    def get_portfolio_value(self, current_prices: dict[str, float]) -> float:
        """
        Return the current total portfolio value.

        Args:
            current_prices: Dict of asset symbol → current market price.
                            Must only contain prices known at the current
                            simulation timestamp (no look-ahead).

        Returns:
            Total portfolio value in quote currency.
        """
        ...
