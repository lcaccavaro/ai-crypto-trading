"""
Unit tests for intrabar execution simulation.

Tests all intrabar scenarios:
    - Stop hit (low <= stop for LONG position)
    - Target hit (high >= target for LONG position)
    - Both stop and target hit same candle:
        - STOP_FIRST policy: stop wins
        - TARGET_FIRST policy: target wins
        - REJECT_AMBIGUOUS policy: no fill
    - Gap through stop (open <= stop): fill at open (FILL_AT_OPEN)
    - Gap through target (open >= target): fill at open (FILL_AT_OPEN)
    - No fill when candle is within range
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


def make_cost_model():
    return CostModel(
        slippage_bps=0.0,
        spread_bps=0.0,
        taker_fee_rate=0.0,
        maker_fee_rate=0.0,
    )


def make_simulator(policy=IntrabarFillPolicy.STOP_FIRST, gap=GapPolicy.FILL_AT_OPEN):
    return ExecutionSimulator(
        cost_model=make_cost_model(),
        intrabar_policy=policy,
        gap_policy=gap,
    )


def make_entry_fill(price=50_000.0, qty=0.001):
    return Fill.create(
        order_id="ord-entry",
        timestamp=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        asset="BTCUSDT",
        side=OrderSide.BUY,
        fill_price=price,
        quantity=qty,
        fees=0.0,
    )


def make_long_position(entry_price=50_000.0, stop=49_000.0, target=53_000.0, qty=0.001):
    entry_fill = make_entry_fill(entry_price, qty)
    return Position.create(
        asset="BTCUSDT",
        side=PositionSide.LONG,
        entry_fill=entry_fill,
        strategy_name="test",
        run_id="test_run",
        stop_price=stop,
        target_price=target,
        initial_stop=stop,
        risk_amount=qty * abs(entry_price - stop),
    )


TS = datetime(2026, 8, 1, 10, 15, tzinfo=timezone.utc)


class TestStopHit:
    def test_long_stop_hit_on_low(self):
        sim = make_simulator()
        pos = make_long_position(stop=49_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=50_200.0,
            candle_low=48_800.0,  # low < stop → stop hit
            candle_close=49_500.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is not None
        assert reason == ExitReason.STOP

    def test_long_stop_not_hit(self):
        sim = make_simulator()
        pos = make_long_position(stop=49_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_100.0,
            candle_high=50_500.0,
            candle_low=49_500.0,  # low > stop → no stop
            candle_close=50_200.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is None
        assert reason is None


class TestTargetHit:
    def test_long_target_hit_on_high(self):
        sim = make_simulator()
        pos = make_long_position(target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=53_500.0,  # high > target → target hit
            candle_low=49_800.0,
            candle_close=53_000.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is not None
        assert reason == ExitReason.TARGET

    def test_long_target_not_hit(self):
        sim = make_simulator()
        pos = make_long_position(target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=50_000.0,
            candle_high=52_900.0,  # high < target → no target
            candle_low=49_800.0,
            candle_close=52_000.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is None
        assert reason is None


class TestIntrabarAmbiguity:
    """Both stop and target touched in same candle."""

    def _ambiguous_candle(self):
        """Returns candle data where both stop (49,000) and target (53,000) are touched."""
        return dict(
            candle_open=50_000.0,
            candle_high=54_000.0,  # >= target (53,000)
            candle_low=48_000.0,   # <= stop (49,000)
            candle_close=50_000.0,
            candle_timestamp=TS,
            run_id="test",
        )

    def test_stop_first_policy(self):
        sim = make_simulator(policy=IntrabarFillPolicy.STOP_FIRST)
        pos = make_long_position(stop=49_000.0, target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(pos, **self._ambiguous_candle())
        assert reason == ExitReason.STOP

    def test_target_first_policy(self):
        sim = make_simulator(policy=IntrabarFillPolicy.TARGET_FIRST)
        pos = make_long_position(stop=49_000.0, target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(pos, **self._ambiguous_candle())
        assert reason == ExitReason.TARGET

    def test_reject_ambiguous_policy(self):
        sim = make_simulator(policy=IntrabarFillPolicy.REJECT_AMBIGUOUS)
        pos = make_long_position(stop=49_000.0, target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(pos, **self._ambiguous_candle())
        assert fill is None
        assert reason is None


class TestGapHandling:
    def test_gap_through_stop_fills_at_open(self):
        """Candle opens below stop — fill at open (FILL_AT_OPEN policy)."""
        sim = make_simulator(gap=GapPolicy.FILL_AT_OPEN)
        pos = make_long_position(stop=49_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=48_000.0,   # opens below stop
            candle_high=48_500.0,
            candle_low=47_000.0,
            candle_close=48_200.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is not None
        assert reason == ExitReason.STOP
        # Fill price should be at open (48,000), not at stop (49,000)
        assert fill.fill_price == pytest.approx(48_000.0)

    def test_gap_through_target_fills_at_open(self):
        """Candle opens above target — fill at open (FILL_AT_OPEN policy)."""
        sim = make_simulator(gap=GapPolicy.FILL_AT_OPEN)
        pos = make_long_position(target=53_000.0)
        fill, reason = sim.check_and_simulate_exits(
            position=pos,
            candle_open=54_000.0,   # opens above target
            candle_high=54_500.0,
            candle_low=53_500.0,
            candle_close=54_000.0,
            candle_timestamp=TS,
            run_id="test",
        )
        assert fill is not None
        assert reason == ExitReason.TARGET
        assert fill.fill_price == pytest.approx(54_000.0)

    def test_normal_candle_no_gap_fill(self):
        """Candle within range — no gap trigger."""
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


class TestEntryFillSimulation:
    def test_market_entry_fill_created(self):
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
        assert fill.fill_price >= 50_000.0  # at or above open (no cost in zero-cost model)

    def test_market_entry_fill_price_equals_open_with_zero_cost(self):
        sim = make_simulator()  # zero cost model
        fill = sim.simulate_market_entry(
            order_id="ord-1",
            timestamp=TS,
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=0.001,
            candle_open=50_000.0,
        )
        assert fill.fill_price == pytest.approx(50_000.0)
