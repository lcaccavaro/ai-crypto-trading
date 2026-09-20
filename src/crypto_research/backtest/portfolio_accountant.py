"""
Portfolio accountant — capital, equity, and PnL tracking.

Responsibilities:
    - Track cash balance (uninvested capital).
    - Track equity (cash + unrealized PnL of all open positions).
    - Track realized and unrealized PnL.
    - Track cumulative costs (fees, slippage, spread).
    - Track daily PnL (resets at UTC day boundary).
    - Calculate drawdown from historical equity peak (no future leakage).
    - Produce PortfolioState snapshots and EquityCurvePoint records.

Accounting definitions:
━━━━━━━━━━━━━━━━━━━━━━━

    cash              = initial_balance
                       - sum(entry_fill.fill_price × qty)      for all open positions
                       + sum(exit_fill.fill_price × qty)       for all closed positions
                       - sum(all_fees)

    equity            = cash + sum(unrealized_pnl of open positions)

    used_capital      = sum(entry_fill.fill_price × qty) for all open positions

    available_capital = cash - max(used_capital - cash, 0)
                      ≈ cash (for positions where capital is not borrowed)
                      In Spot mode: available = cash (no leverage).
                      This simplification holds for Prompt 03.

    gross_exposure    = sum(|notional|) = sum(qty × current_price)

    net_exposure      = sum(notional × sign): +1 for LONG, -1 for SHORT

    realized_pnl      = sum(net_pnl of all closed trades)

    unrealized_pnl    = sum(unrealized_pnl of all open positions)

    daily_pnl         = realized_pnl since last UTC midnight
                       + change in unrealized PnL since last UTC midnight

Drawdown calculation (no future leakage):
    peak_equity       = max(equity seen so far in the simulation)
    drawdown          = (equity - peak_equity) / peak_equity
    Updated at every equity curve snapshot — never using future equity.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from crypto_research.core.domain import (
    EquityCurvePoint,
    Fill,
    OrderSide,
    Position,
    PortfolioState,
    PositionSide,
    Trade,
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PortfolioAccountant:
    """
    Stateful portfolio accounting ledger.

    One instance per backtest run. Updated by the engine at every fill,
    position open, and position close event.

    Thread safety: Not thread-safe. Single-threaded event loop only.
    """

    def __init__(self, initial_balance: float) -> None:
        """
        Args:
            initial_balance: Starting capital in quote currency (USDT).
        """
        if initial_balance <= 0:
            raise ValueError(
                f"initial_balance must be positive, got {initial_balance}"
            )

        self._initial_balance = initial_balance
        self._cash = initial_balance
        self._realized_pnl = 0.0
        self._total_fees = 0.0
        self._total_slippage = 0.0
        self._total_spread_cost = 0.0
        self._daily_pnl = 0.0
        self._daily_start_equity = initial_balance

        # Open positions tracked for unrealized PnL and exposure
        self._open_positions: dict[str, Position] = {}  # position_id → Position

        # Equity curve history
        self._equity_curve: list[EquityCurvePoint] = []

        # Peak equity for drawdown calculation (no future leakage)
        self._peak_equity = initial_balance

        # Current-day start for daily tracking
        self._current_day: Optional[int] = None  # UTC day-of-year × year

    # ------------------------------------------------------------------
    # Event handlers (called by engine)
    # ------------------------------------------------------------------

    def on_entry_fill(self, fill: Fill, position: Position) -> None:
        """
        Update accounting state when an entry fill occurs.

        Deducts the capital used from cash. Registers the open position.

        Args:
            fill:     Entry fill.
            position: Position opened by this fill.
        """
        notional = fill.fill_price * fill.quantity
        # Cash decreases by notional value + fees on entry
        self._cash -= notional + fill.fees
        self._total_fees += fill.fees
        self._total_slippage += fill.slippage
        self._total_spread_cost += fill.spread_cost
        self._open_positions[position.position_id] = position

        logger.debug(
            "Portfolio: entry fill recorded",
            position_id=position.position_id,
            symbol=position.asset,
            notional=round(notional, 4),
            cash_after=round(self._cash, 4),
        )

    def on_exit_fill(
        self, trade: Trade, position: Position, exit_fill: Fill
    ) -> None:
        """
        Update accounting state when an exit fill occurs.

        Returns proceeds to cash, updates realized PnL, removes position.

        Args:
            trade:     Completed trade record.
            position:  Position being closed.
            exit_fill: Exit fill.
        """
        notional_returned = exit_fill.fill_price * exit_fill.quantity
        # Cash increases by exit notional minus exit fees
        self._cash += notional_returned - exit_fill.fees
        self._realized_pnl += trade.net_pnl
        self._daily_pnl += trade.net_pnl
        self._total_fees += exit_fill.fees
        self._total_slippage += exit_fill.slippage
        self._total_spread_cost += exit_fill.spread_cost

        if position.position_id in self._open_positions:
            del self._open_positions[position.position_id]

        logger.debug(
            "Portfolio: exit fill recorded",
            position_id=position.position_id,
            symbol=position.asset,
            net_pnl=round(trade.net_pnl, 4),
            realized_pnl_cumulative=round(self._realized_pnl, 4),
            cash_after=round(self._cash, 4),
        )

    def update_position_price(self, position_id: str, current_price: float) -> None:
        """Update the current market price of an open position (for unrealized PnL)."""
        if position_id in self._open_positions:
            self._open_positions[position_id].current_price = current_price

    def check_and_reset_daily(self, timestamp: datetime) -> bool:
        """
        Check if we have crossed into a new UTC day. If so, reset daily PnL.

        Args:
            timestamp: Current simulation timestamp (UTC-aware).

        Returns:
            True if the daily counter was reset.
        """
        day_key = timestamp.toordinal()
        if self._current_day is None:
            self._current_day = day_key
            return False

        if day_key != self._current_day:
            logger.info(
                "Daily PnL reset",
                previous_daily_pnl=round(self._daily_pnl, 4),
                new_day=timestamp.date().isoformat(),
            )
            self._daily_pnl = 0.0
            self._daily_start_equity = self.get_equity(
                {pid: pos.current_price for pid, pos in self._open_positions.items()
                 if pos.current_price is not None}
            )
            self._current_day = day_key
            return True
        return False

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_unrealized_pnl(self, current_prices: dict[str, float] | None = None) -> float:
        """
        Calculate total unrealized PnL across all open positions.

        Args:
            current_prices: Optional dict of symbol → price.
                            If provided, updates position prices first.

        Returns:
            Total unrealized PnL in quote currency.
        """
        if current_prices:
            for pos in self._open_positions.values():
                if pos.asset in current_prices:
                    pos.current_price = current_prices[pos.asset]

        total = 0.0
        for pos in self._open_positions.values():
            upnl = pos.unrealized_pnl
            if upnl is not None:
                total += upnl
        return total

    def get_equity(self, current_prices: dict[str, float] | None = None) -> float:
        """Total portfolio equity = cash + unrealized PnL."""
        return self._cash + self.get_unrealized_pnl(current_prices)

    def get_gross_exposure(self) -> float:
        """Sum of absolute notional values of all open positions."""
        total = 0.0
        for pos in self._open_positions.values():
            total += pos.notional
        return total

    def get_net_exposure(self) -> float:
        """Net directional exposure: +notional for LONG, -notional for SHORT."""
        total = 0.0
        for pos in self._open_positions.values():
            sign = 1.0 if pos.side == PositionSide.LONG else -1.0
            total += sign * pos.notional
        return total

    def get_asset_notional(self, symbol: str) -> float:
        """Total notional exposure for a specific symbol."""
        total = 0.0
        for pos in self._open_positions.values():
            if pos.asset == symbol:
                total += pos.notional
        return total

    def get_available_capital(self, equity: float | None = None) -> float:
        """
        Capital available for new positions.

        In Spot mode (Prompt 03): available_capital = cash.
        (No leverage — cannot use unrealized gains as collateral.)
        """
        return max(0.0, self._cash)

    def get_portfolio_state(
        self,
        timestamp: datetime,
        current_prices: dict[str, float] | None = None,
    ) -> PortfolioState:
        """
        Create a PortfolioState snapshot at the given timestamp.

        Args:
            timestamp:      Current simulation timestamp.
            current_prices: Symbol → price for unrealized PnL calculation.

        Returns:
            Complete PortfolioState snapshot.
        """
        unrealized = self.get_unrealized_pnl(current_prices)
        equity = self._cash + unrealized
        gross_exp = self.get_gross_exposure()
        net_exp = self.get_net_exposure()
        available = self.get_available_capital(equity)

        return PortfolioState(
            timestamp=timestamp,
            cash=self._cash,
            equity=equity,
            used_capital=gross_exp,
            available_capital=available,
            gross_exposure=gross_exp,
            net_exposure=net_exp,
            realized_pnl=self._realized_pnl,
            unrealized_pnl=unrealized,
            total_fees=self._total_fees,
            total_slippage=self._total_slippage,
            total_spread_cost=self._total_spread_cost,
            daily_pnl=self._daily_pnl,
        )

    def snapshot_equity_curve(
        self,
        timestamp: datetime,
        current_prices: dict[str, float] | None = None,
    ) -> EquityCurvePoint:
        """
        Record an equity curve snapshot and return it.

        Drawdown is calculated from the historical peak equity — never using
        future equity values. This is point-in-time correct.

        Args:
            timestamp:      Current simulation timestamp.
            current_prices: Symbol → price for equity calculation.

        Returns:
            EquityCurvePoint appended to internal equity curve history.
        """
        state = self.get_portfolio_state(timestamp, current_prices)
        equity = state.equity

        # Update peak equity (no future leakage — peak is only updated forward)
        if equity > self._peak_equity:
            self._peak_equity = equity

        drawdown = (equity - self._peak_equity) / self._peak_equity if self._peak_equity > 0 else 0.0

        point = EquityCurvePoint(
            timestamp=timestamp,
            cash=state.cash,
            equity=equity,
            realized_pnl=state.realized_pnl,
            unrealized_pnl=state.unrealized_pnl,
            gross_exposure=state.gross_exposure,
            net_exposure=state.net_exposure,
            drawdown=drawdown,
        )
        self._equity_curve.append(point)
        return point

    @property
    def equity_curve(self) -> list[EquityCurvePoint]:
        """All equity curve snapshots recorded so far."""
        return list(self._equity_curve)

    @property
    def open_positions(self) -> list[Position]:
        """Currently open positions."""
        return list(self._open_positions.values())

    @property
    def open_position_count(self) -> int:
        """Number of currently open positions."""
        return len(self._open_positions)

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl

    @property
    def total_fees(self) -> float:
        return self._total_fees

    @property
    def total_slippage(self) -> float:
        return self._total_slippage

    @property
    def total_spread_cost(self) -> float:
        return self._total_spread_cost

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def initial_balance(self) -> float:
        return self._initial_balance
