"""
Risk manager interface for the crypto research laboratory.

Defines the Protocol for risk evaluation before any order is submitted.
Prompt 05 will implement the full risk management logic.

Risk management principles:
    - Every signal MUST be evaluated by the risk manager before an order is created.
    - The risk manager is the only component allowed to approve or reject trades.
    - Risk parameters must be configurable (never hard-coded).
    - Risk decisions must be logged with full justification.

Configurable constraints (implemented in Prompt 05):
    - Risk per trade (% of capital)
    - Maximum concurrent positions
    - Maximum total exposure
    - Daily loss limit
    - Daily profit target
    - Risk/reward ratio enforcement
    - Strategy-level exposure limits
    - Asset-level exposure limits
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from crypto_research.core.domain import RiskDecision, Signal


@runtime_checkable
class RiskManager(Protocol):
    """
    Contract for all risk management implementations.

    The risk manager receives a trading Signal and the current portfolio
    state, and decides whether the trade is permitted. If approved, it
    also specifies the maximum allowed position size and risk amount.

    IMPORTANT: The risk manager must use only information available at the
    current simulation timestamp. It must not look ahead to evaluate
    whether a trade will be profitable.
    """

    def evaluate(
        self,
        signal: Signal,
        portfolio_state: dict[str, Any],
    ) -> RiskDecision:
        """
        Evaluate a trading signal against the current portfolio state.

        Args:
            signal:          The signal to evaluate.
            portfolio_state: Dict containing current portfolio metrics:
                - 'capital': float — total account capital
                - 'open_positions': list[Position] — currently open positions
                - 'daily_pnl': float — realized P&L for today
                - 'daily_trade_count': int — number of trades today
                - Any other risk-relevant state

        Returns:
            RiskDecision with approved=True and sizing info if the trade is
            permitted, or approved=False with the rejection reason.

        Note:
            A rejection is NOT an error — it is a valid outcome.
            RiskDecision.reason must always explain the decision.
        """
        ...

    def on_trade_closed(self, trade_result: Any) -> None:
        """
        Notify the risk manager that a trade has closed.

        This allows the risk manager to update daily P&L tracking, position
        counts, and other stateful risk metrics.

        Args:
            trade_result: The completed Trade object.
        """
        ...

    def on_day_start(self, date: Any, capital: float) -> None:
        """
        Notify the risk manager that a new trading day has started.

        Resets daily counters (daily P&L, daily trade count, etc.).

        Args:
            date:    The new trading date.
            capital: Total capital at the start of the day.
        """
        ...
