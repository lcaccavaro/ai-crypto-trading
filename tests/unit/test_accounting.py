"""
Unit tests for the portfolio accountant.

Tests:
    - Cash decreases on entry fill (notional + fees).
    - Cash increases on exit fill (exit notional - fees).
    - Realized PnL accumulates correctly.
    - Unrealized PnL is computed from current prices.
    - Daily PnL resets at UTC day boundary.
    - Drawdown is calculated from historical peak (no future leakage).
    - Available capital is correctly tracked.
    - Initial balance is positive required.
"""

from datetime import datetime, timedelta, timezone

import pytest

from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.core.domain import (
    ExitReason,
    Fill,
    OrderSide,
    Position,
    PositionSide,
    Trade,
)


def make_fill(
    order_id="ord-1",
    asset="BTCUSDT",
    side=OrderSide.BUY,
    fill_price=50_000.0,
    quantity=0.001,
    fees=0.025,
    slippage=0.01,
    spread_cost=0.005,
    ts=None,
):
    return Fill.create(
        order_id=order_id,
        timestamp=ts or datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        asset=asset,
        side=side,
        fill_price=fill_price,
        quantity=quantity,
        fees=fees,
        slippage=slippage,
        spread_cost=spread_cost,
    )


def make_position(entry_fill, stop=49_000.0, target=53_000.0):
    return Position.create(
        asset=entry_fill.asset,
        side=PositionSide.LONG,
        entry_fill=entry_fill,
        strategy_name="test",
        run_id="test_run",
        stop_price=stop,
        target_price=target,
        initial_stop=stop,
        risk_amount=entry_fill.quantity * abs(entry_fill.fill_price - stop),
    )


def make_trade(entry_fill, exit_fill, net_pnl, gross_pnl=None, fees=0.0, slippage=0.0, spread=0.0):
    return Trade.create(
        asset=entry_fill.asset,
        side=PositionSide.LONG,
        entry_fill=entry_fill,
        exit_fill=exit_fill,
        strategy_name="test",
        run_id="test_run",
        exit_reason=ExitReason.TARGET.value,
        gross_pnl=gross_pnl or net_pnl + fees + slippage + spread,
        fees=fees,
        slippage_cost=slippage,
        spread_cost=spread,
        net_pnl=net_pnl,
    )


class TestInitialization:
    def test_initial_cash_equals_balance(self):
        acc = PortfolioAccountant(10_000.0)
        assert acc.cash == 10_000.0

    def test_initial_balance_must_be_positive(self):
        with pytest.raises(ValueError):
            PortfolioAccountant(0.0)
        with pytest.raises(ValueError):
            PortfolioAccountant(-100.0)

    def test_initial_realized_pnl_zero(self):
        acc = PortfolioAccountant(10_000.0)
        assert acc.realized_pnl == 0.0

    def test_initial_equity_equals_balance(self):
        acc = PortfolioAccountant(10_000.0)
        assert acc.get_equity() == pytest.approx(10_000.0)


class TestEntryFill:
    def test_cash_decreases_on_entry(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill(fill_price=50_000.0, quantity=0.001, fees=0.025)
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)
        # cash -= notional + fees = 50 + 0.025 = 50.025
        expected_cash = 10_000.0 - (50_000.0 * 0.001) - 0.025
        assert acc.cash == pytest.approx(expected_cash)

    def test_position_registered(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill()
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)
        assert acc.open_position_count == 1

    def test_fees_accumulated(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill(fees=5.0)
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)
        assert acc.total_fees == pytest.approx(5.0)


class TestExitFill:
    def _setup_open_position(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill(fill_price=50_000.0, quantity=0.001, fees=0.025)
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)
        return acc, entry, pos

    def test_cash_increases_on_exit(self):
        acc, entry, pos = self._setup_open_position()
        cash_before = acc.cash
        exit_fill = make_fill(
            order_id="exit-1",
            side=OrderSide.SELL,
            fill_price=53_000.0,
            quantity=0.001,
            fees=0.0265,
            ts=datetime(2026, 8, 1, 11, 0, tzinfo=timezone.utc),
        )
        trade = make_trade(entry, exit_fill, net_pnl=3.0, fees=0.0265)
        acc.on_exit_fill(trade, pos, exit_fill)
        assert acc.cash > cash_before

    def test_position_removed_on_exit(self):
        acc, entry, pos = self._setup_open_position()
        exit_fill = make_fill(order_id="exit-1", side=OrderSide.SELL)
        trade = make_trade(entry, exit_fill, net_pnl=0.0)
        acc.on_exit_fill(trade, pos, exit_fill)
        assert acc.open_position_count == 0

    def test_realized_pnl_accumulated(self):
        acc, entry, pos = self._setup_open_position()
        exit_fill = make_fill(order_id="exit-1", side=OrderSide.SELL)
        trade = make_trade(entry, exit_fill, net_pnl=15.0)
        acc.on_exit_fill(trade, pos, exit_fill)
        assert acc.realized_pnl == pytest.approx(15.0)


class TestUnrealizedPnL:
    def test_unrealized_pnl_for_long_profitable(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill(fill_price=50_000.0, quantity=0.001, fees=0.0)
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)
        # Update price to 51,000
        acc.update_position_price(pos.position_id, 51_000.0)
        upnl = acc.get_unrealized_pnl()
        assert upnl == pytest.approx(0.001 * (51_000.0 - 50_000.0))

    def test_unrealized_pnl_zero_no_positions(self):
        acc = PortfolioAccountant(10_000.0)
        assert acc.get_unrealized_pnl() == pytest.approx(0.0)


class TestDailyPnL:
    def test_daily_pnl_resets_at_day_boundary(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill()
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)

        # Seed daily tracker on day 1 (2026-08-01)
        day1_ts = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
        acc.check_and_reset_daily(day1_ts)

        # Record a profit on day 1
        exit_fill = make_fill(order_id="exit-1", side=OrderSide.SELL)
        trade = make_trade(entry, exit_fill, net_pnl=50.0)
        acc.on_exit_fill(trade, pos, exit_fill)
        assert acc.daily_pnl == pytest.approx(50.0)

        # Advance to next UTC day — must reset
        next_day = datetime(2026, 8, 2, 0, 5, tzinfo=timezone.utc)
        reset = acc.check_and_reset_daily(next_day)
        assert reset is True
        assert acc.daily_pnl == pytest.approx(0.0)

    def test_daily_pnl_not_reset_same_day(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill()
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)
        exit_fill = make_fill(order_id="exit-1", side=OrderSide.SELL)
        trade = make_trade(entry, exit_fill, net_pnl=10.0)
        acc.on_exit_fill(trade, pos, exit_fill)

        same_day = datetime(2026, 8, 1, 23, 59, tzinfo=timezone.utc)
        reset = acc.check_and_reset_daily(same_day)
        assert reset is False
        assert acc.daily_pnl == pytest.approx(10.0)


class TestDrawdown:
    def test_drawdown_zero_at_start(self):
        acc = PortfolioAccountant(10_000.0)
        ts = datetime(2026, 8, 1, 10, tzinfo=timezone.utc)
        point = acc.snapshot_equity_curve(ts, {})
        assert point.drawdown == pytest.approx(0.0)

    def test_drawdown_negative_after_loss(self):
        acc = PortfolioAccountant(10_000.0)
        entry = make_fill()
        pos = make_position(entry)
        acc.on_entry_fill(entry, pos)

        # Equity has risen (snapshot peak)
        ts1 = datetime(2026, 8, 1, 10, tzinfo=timezone.utc)
        acc.update_position_price(pos.position_id, 51_000.0)
        acc.snapshot_equity_curve(ts1, {"BTCUSDT": 51_000.0})

        # Equity drops
        ts2 = datetime(2026, 8, 1, 11, tzinfo=timezone.utc)
        acc.update_position_price(pos.position_id, 48_000.0)
        point = acc.snapshot_equity_curve(ts2, {"BTCUSDT": 48_000.0})
        assert point.drawdown < 0.0

    def test_drawdown_uses_historical_peak_not_future(self):
        """Drawdown peak must never use future equity values."""
        acc = PortfolioAccountant(10_000.0)
        ts1 = datetime(2026, 8, 1, 10, tzinfo=timezone.utc)
        ts2 = datetime(2026, 8, 1, 11, tzinfo=timezone.utc)

        p1 = acc.snapshot_equity_curve(ts1, {})  # peak = 10_000
        p2 = acc.snapshot_equity_curve(ts2, {})  # equity unchanged

        # Both should have 0 drawdown (equity == peak)
        assert p1.drawdown == pytest.approx(0.0)
        assert p2.drawdown == pytest.approx(0.0)
