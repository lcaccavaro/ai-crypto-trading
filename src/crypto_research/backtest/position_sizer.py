"""
Position sizing for the backtest engine.

Implements two sizing modes:
    RISK_BASED — Size determined by dollar risk budget and stop distance.
    FIXED      — Fixed quantity per trade (testing/validation only).

Risk-based sizing formula:
━━━━━━━━━━━━━━━━━━━━━━━━━

    risk_budget = equity × risk_per_trade_pct / 100

    stop_distance = |entry_price - stop_price|

    quantity = risk_budget / stop_distance

If the calculated quantity exceeds available capital:
    The trade is rejected (INSUFFICIENT_CAPITAL).
    This is an explicit, logged rejection — never a silent reduction.

R-multiple interpretation:
    1R  = risk_budget (the amount put at risk)
    +3R = profit of 3 × risk_budget (at a 3:1 R/R target)
    -1R = full stop hit, loss of risk_budget

NOTE: Costs (slippage, spread, fees) are NOT subtracted from the risk
budget at sizing time. They are captured in the fill and reduce net PnL.
Sizing is based on the theoretical stop distance for clarity.
"""

from __future__ import annotations

from crypto_research.core.exceptions import ExecutionError


class PositionSizer:
    """
    Stateless position sizing calculator.

    Usage:
        sizer = PositionSizer()
        qty = sizer.size_risk_based(
            equity=10_000,
            risk_per_trade_pct=1.0,
            entry_price=50_000,
            stop_price=49_000,
            available_capital=10_000,
        )
    """

    def size_risk_based(
        self,
        equity: float,
        risk_per_trade_pct: float,
        entry_price: float,
        stop_price: float,
        available_capital: float,
    ) -> float:
        """
        Calculate position size using risk-based sizing.

        Formula:
            risk_budget   = equity × risk_per_trade_pct / 100
            stop_distance = |entry_price - stop_price|
            quantity      = risk_budget / stop_distance

        The resulting notional value (quantity × entry_price) is checked
        against available_capital. If it exceeds available capital, raises
        ExecutionError — the trade must be rejected at the risk gate.

        Args:
            equity:             Current portfolio equity.
            risk_per_trade_pct: % of equity at risk if stop is hit (e.g. 1.0).
            entry_price:        Anticipated entry price.
            stop_price:         Stop-loss level.
            available_capital:  Capital currently available for new positions.

        Returns:
            Calculated position quantity in base asset units.

        Raises:
            ExecutionError: If stop_distance is zero or negative.
            ExecutionError: If calculated notional exceeds available capital.
        """
        if equity <= 0:
            raise ExecutionError(f"Equity must be positive for risk-based sizing, got {equity}")

        stop_distance = abs(entry_price - stop_price)
        if stop_distance <= 0:
            raise ExecutionError(
                f"Stop distance must be positive for risk-based sizing. "
                f"entry={entry_price}, stop={stop_price}, distance={stop_distance}"
            )

        risk_budget = equity * risk_per_trade_pct / 100.0
        quantity = risk_budget / stop_distance

        required_capital = quantity * entry_price
        if required_capital > available_capital:
            raise ExecutionError(
                f"Calculated position requires {required_capital:.2f} USDT "
                f"but only {available_capital:.2f} USDT is available. "
                f"Trade must be rejected (INSUFFICIENT_CAPITAL)."
            )

        return quantity

    def size_fixed(
        self,
        fixed_quantity: float,
        entry_price: float,
        available_capital: float,
    ) -> float:
        """
        Return a fixed quantity, validating it fits within available capital.

        This mode is for unit testing and engine validation only.
        It must NOT be used for research that claims to simulate realistic
        position management.

        Args:
            fixed_quantity:     Configured fixed quantity.
            entry_price:        Anticipated entry price.
            available_capital:  Capital currently available.

        Returns:
            fixed_quantity (unchanged).

        Raises:
            ExecutionError: If fixed_quantity × entry_price > available_capital.
        """
        if fixed_quantity <= 0:
            raise ExecutionError(
                f"fixed_quantity must be positive, got {fixed_quantity}"
            )

        required_capital = fixed_quantity * entry_price
        if required_capital > available_capital:
            raise ExecutionError(
                f"Fixed quantity {fixed_quantity} requires {required_capital:.2f} USDT "
                f"but only {available_capital:.2f} USDT is available. "
                f"Trade must be rejected (INSUFFICIENT_CAPITAL)."
            )

        return fixed_quantity

    def compute_risk_amount(
        self, quantity: float, entry_price: float, stop_price: float
    ) -> float:
        """
        Compute the dollar risk amount for a position.

        risk_amount = quantity × |entry_price - stop_price|

        This is the maximum dollar loss if the stop is hit exactly
        (before accounting for slippage/fees on the exit fill).

        Args:
            quantity:     Position size in base asset.
            entry_price:  Entry fill price.
            stop_price:   Stop-loss price.

        Returns:
            Dollar risk amount (positive).
        """
        return quantity * abs(entry_price - stop_price)

    def compute_r_multiple(self, net_pnl: float, risk_amount: float) -> float:
        """
        Compute the R-multiple for a completed trade.

        R-multiple = net_pnl / risk_amount

        Interpretation:
            +3.0  = profit of 3R (hit target on a 3:1 R/R setup)
            -1.0  = loss of 1R (stop hit)
            +0.5  = partial profit (closed before target)

        Mathematically:
            1 win + 3 losses (at 3:1 R/R) = +3R - 3R = 0R before costs.
            This is the 25% break-even win rate for a 3:1 payoff structure.

        Args:
            net_pnl:     Net PnL (after all costs) of the completed trade.
            risk_amount: Dollar risk at entry (qty × |entry - stop|).

        Returns:
            R-multiple (float). Positive = winner, negative = loser.

        Raises:
            ExecutionError: If risk_amount is zero (undefined R).
        """
        if risk_amount == 0:
            raise ExecutionError(
                "Cannot compute R-multiple: risk_amount is zero. "
                "Check that stop_price differs from entry_price."
            )
        return net_pnl / risk_amount
