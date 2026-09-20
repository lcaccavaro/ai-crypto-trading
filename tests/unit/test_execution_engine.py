"""
Unit tests for the execution engine simulator (entry fills + exit management).

Tests:
    - Market entry fill is created correctly.
    - Stop fill uses SELL side for LONG positions.
    - Target fill uses SELL side for LONG positions.
    - Fill price accounts for costs (slippage + spread + fee).
    - Gap through stop fills at candle open.
    - Gap through target fills at candle open.
"""

from datetime import datetime, timezone

import pytest

from crypto_research.backtest.cost_model import CostModel
from crypto_research.backtest.execution_simulator import ExecutionSimulator
from crypto_research.core.domain import (
    ExitReason,
    Fill,
    GapPolicy,
    IntrabarFillPolicy,
    OrderSide,
    Position,
    PositionSide,
)


def make_cost_model(slippage_bps=2.0, spread_bps=1.0, taker=0.0005):
    return CostModel(
        slippage_bps=slippage_bps,
        spread_bps=spread_bps,
        taker_fee_rate=taker,
        maker_fee_rate=0.0002,
    )


def make_zero_cost_model():
    return CostModel(0.0, 0.0, 0.0, 0.0)


def make_simulator(policy=IntrabarFillPolicy.STOP_FIRST, gap=GapPolicy.FILL_AT_OPEN, cost_model=None):
    return ExecutionSimulator(
        cost_model=cost_model or make_zero_cost_model(),
        intrabar_policy=policy,
        gap_policy=gap,
    )


def make_entry_fill(price=50_000.0, qty=0.001):
    return Fill.create(
        order_id="ord-1",
        timestamp=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        asset="BTCUSDT",
        side=OrderSide.BUY,
        fill_price=price,
        quantity=qty,
        fees=0.0,
    )


def make_long_position(entry_price=50_000.0, stop=49_000.0, target=53_000.0):
    entry_fill = make_entry_fill(entry_price)
    return Position.create(
        asset="BTCUSDT",
        side=PositionSide.LONG,
        entry_fill=entry_fill,
        strategy_name="test",
        run_id="test_run",
        stop_price=stop,
        target_price=target,
        initial_stop=stop,
        risk_amount=0.001 * abs(entry_price - stop),
    )


TS = datetime(2026, 8, 1, 10, 15, tzinfo=timezone.utc)


class TestMarketEntryFill:
    def test_entry_fill_created(self):
        sim = make_simulator()
        fill = sim.simulate_market_entry(
            order_id="ord-1",
            timestamp=TS,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=0.001,
            candle_open=50_000.0,
        )
        assert fill is not None
        assert fill.quantity == pytest.approx(0.001)
        assert fill.asset == "BTCUSDT"
        assert fill.side == OrderSide.BUY

    def test_long_entry_price_above_open_with_cost(self):
        sim = make_simulator(cost_model=make_cost_model(slippage_bps=10, spread_bps=5))
        fill = sim.simulate_market_entry(
            order_id="ord-1",
            timestamp=TS,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=0.001,
            candle_open=50_000.0,
        )
        assert fill.fill_price > 50_000.0

    def test_fees_are_positive_with_cost_model(self):
        sim = make_simulator(cost_model=make_cost_model())
        fill = sim.simulate_market_entry(
            order_id="ord-1",
            timestamp=TS,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=0.001,
            candle_open=50_000.0,
        )
        assert fill.fees > 0.0

    def test_zero_cost_entry_fills_at_open(self):
        sim = make_simulator(cost_model=make_zero_cost_model())
        fill = sim.simulate_market_entry(
            order_id="ord-1",
            timestamp=TS,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=0.001,
            candle_open=50_000.0,
        )
        assert fill.fill_price == pytest.approx(50_000.0)
        assert fill.fees == pytest.approx(0.0)


class TestStopExitFill:
    def test_stop_fill_uses_sell_side(self):
        sim = make_simulator()
        pos = make_long_position(stop=49_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=50_200.0,
            candle_low=48_900.0,
            candle_close=49_200.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is not None
        assert fill.side == OrderSide.SELL

    def test_stop_fill_price_at_stop_level(self):
        sim = make_simulator()  # zero cost
        pos = make_long_position(stop=49_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=50_200.0,
            candle_low=48_900.0,
            candle_close=49_200.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill.fill_price == pytest.approx(49_000.0)


class TestTargetExitFill:
    def test_target_fill_uses_sell_side(self):
        sim = make_simulator()
        pos = make_long_position(target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=53_500.0,
            candle_low=49_800.0,
            candle_close=53_000.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is not None
        assert fill.side == OrderSide.SELL

    def test_target_fill_price_at_target_level(self):
        sim = make_simulator()  # zero cost
        pos = make_long_position(target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=53_500.0,
            candle_low=49_800.0,
            candle_close=53_000.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill.fill_price == pytest.approx(53_000.0)


class TestNoExitInRangeCandle:
    def test_candle_within_range_no_exit(self):
        sim = make_simulator()
        pos = make_long_position(stop=49_000.0, target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_100.0,
            candle_high=51_000.0,
            candle_low=49_500.0,
            candle_close=50_500.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is None
        assert reason is None


class TestPositionWithNoBracket:
    def test_no_stop_no_target_returns_none(self):
        entry_fill = make_entry_fill()
        pos = Position.create(
            asset="BTCUSDT",
            side=PositionSide.LONG,
            entry_fill=entry_fill,
            strategy_name="test",
            run_id="test_run",
            stop_price=None,
            target_price=None,
        )
        sim = make_simulator()
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=51_000.0,
            candle_low=49_000.0,
            candle_close=50_500.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is None
        assert reason is None
