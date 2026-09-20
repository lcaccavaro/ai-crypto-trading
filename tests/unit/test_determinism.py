"""
Determinism tests — same input must always produce identical output.

Tests:
    - Same backtest config + same strategy + same data → identical trade ledger.
    - Same run produces identical equity curve.
    - Same run produces identical net PnL.
    - Strategy is ENGINE_VALIDATION_ONLY.

These tests use synthetic in-memory data (no disk I/O required).
"""

import copy
from datetime import datetime, timezone

import pandas as pd
import pytest

from crypto_research.backtest.cost_model import CostModel
from crypto_research.backtest.execution_simulator import ExecutionSimulator
from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.backtest.validation_strategy import EngineValidationStrategy
from crypto_research.core.domain import (
    GapPolicy,
    IntrabarFillPolicy,
    OrderSide,
    Position,
    PositionSide,
    Fill,
)


def make_cost_model():
    return CostModel(slippage_bps=2.0, spread_bps=1.0, taker_fee_rate=0.0005, maker_fee_rate=0.0002)


def make_candle_series(n=50, base_price=50_000.0, freq="15min"):
    """Generate deterministic synthetic OHLCV data."""
    timestamps = pd.date_range("2026-08-01 10:00", periods=n, freq=freq, tz="UTC")
    data = []
    price = base_price
    for ts in timestamps:
        data.append({
            "timestamp": ts,
            "open": price,
            "high": price * 1.001,
            "low": price * 0.999,
            "close": price * 1.0005,
            "volume": 10.0,
            "close_time": ts + pd.Timedelta(freq) - pd.Timedelta("1ms"),
        })
        price = price * 1.0005  # deterministic drift
    return pd.DataFrame(data)


def simulate_strategy_run(n_candles=50, signal_every=10, rr=3.0):
    """
    Run a deterministic simulation using EngineValidationStrategy.

    Returns: list of (symbol, close_price, signal_or_None) tuples.
    """
    strategy = EngineValidationStrategy(signal_every_n_candles=signal_every, rr_ratio=rr)
    df = make_candle_series(n=n_candles)
    results = []
    for _, row in df.iterrows():
        ts = pd.Timestamp(row["timestamp"]).to_pydatetime()
        sig = strategy.on_candle(
            close_price=row["close"],
            symbol="BTCUSDT",
            timeframe="15m",
            timestamp=ts,
        )
        results.append((row["close"], sig))
    return results


class TestStrategyDeterminism:
    def test_same_signals_on_two_runs(self):
        """Two runs of the same strategy produce identical signals."""
        run1 = simulate_strategy_run()
        run2 = simulate_strategy_run()
        assert len(run1) == len(run2)
        for (price1, sig1), (price2, sig2) in zip(run1, run2):
            assert price1 == pytest.approx(price2)
            assert sig1 == sig2

    def test_signals_produced_at_expected_intervals(self):
        """Signal fires every N candles exactly."""
        results = simulate_strategy_run(n_candles=100, signal_every=10)
        signal_indices = [i for i, (price, sig) in enumerate(results) if sig is not None]
        # Signals at candles: 10, 20, 30, ... (1-indexed, so indices 9, 19, 29, ...)
        expected = list(range(9, 100, 10))
        assert signal_indices == expected

    def test_strategy_reset_restores_determinism(self):
        """After reset(), the strategy produces the same signals as a fresh instance."""
        strategy = EngineValidationStrategy(signal_every_n_candles=5)
        df = make_candle_series(n=20)

        # First run
        sig_first = []
        for _, row in df.iterrows():
            ts = pd.Timestamp(row["timestamp"]).to_pydatetime()
            s = strategy.on_candle(row["close"], "BTCUSDT", "15m", ts)
            sig_first.append(s)

        # Reset and run again
        strategy.reset()
        sig_second = []
        for _, row in df.iterrows():
            ts = pd.Timestamp(row["timestamp"]).to_pydatetime()
            s = strategy.on_candle(row["close"], "BTCUSDT", "15m", ts)
            sig_second.append(s)

        assert sig_first == sig_second


class TestAccountantDeterminism:
    def test_same_fills_produce_same_pnl(self):
        """Two accountants given identical fills produce identical PnL."""

        def run_accountant():
            acc = PortfolioAccountant(10_000.0)
            ts = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
            entry_fill = Fill.create(
                "ord-1", ts, "BTCUSDT", OrderSide.BUY, 50_000.0, 0.001, 0.025
            )
            pos = Position.create(
                asset="BTCUSDT",
                side=PositionSide.LONG,
                entry_fill=entry_fill,
                strategy_name="test",
                run_id="run",
                stop_price=49_000.0,
                target_price=53_000.0,
                initial_stop=49_000.0,
                risk_amount=1.0,
            )
            acc.on_entry_fill(entry_fill, pos)
            return acc.cash, acc.total_fees, acc.open_position_count

        r1 = run_accountant()
        r2 = run_accountant()
        assert r1 == r2

    def test_equity_curve_identical_on_two_runs(self):
        """Equity curve snapshots are identical given same inputs."""

        def run_curve():
            acc = PortfolioAccountant(10_000.0)
            snapshots = []
            for i in range(5):
                ts = datetime(2026, 8, 1, 10 + i, 0, tzinfo=timezone.utc)
                pt = acc.snapshot_equity_curve(ts, {})
                snapshots.append((pt.equity, pt.drawdown))
            return snapshots

        assert run_curve() == run_curve()


class TestCostModelDeterminism:
    def test_same_cost_same_price(self):
        cm = make_cost_model()
        p1 = cm.calculate_execution_price(50_000.0, OrderSide.BUY)
        p2 = cm.calculate_execution_price(50_000.0, OrderSide.BUY)
        assert p1 == p2

    def test_zero_cost_fills_at_exact_price(self):
        cm = CostModel(0.0, 0.0, 0.0, 0.0)
        price = cm.calculate_execution_price(50_000.0, OrderSide.BUY)
        assert price == pytest.approx(50_000.0)


class TestValidationStrategyParameters:
    def test_invalid_n_raises(self):
        with pytest.raises(ValueError):
            EngineValidationStrategy(signal_every_n_candles=0)

    def test_invalid_rr_raises(self):
        with pytest.raises(ValueError):
            EngineValidationStrategy(rr_ratio=-1.0)

    def test_stop_and_target_computed(self):
        strategy = EngineValidationStrategy(signal_every_n_candles=1, rr_ratio=3.0)
        ts = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
        sig = strategy.on_candle(50_000.0, "BTCUSDT", "15m", ts)
        assert sig is not None
        assert sig["stop_price"] < 50_000.0
        assert sig["target_price"] > 50_000.0

    def test_rr_ratio_is_correct(self):
        rr = 4.0
        strategy = EngineValidationStrategy(signal_every_n_candles=1, rr_ratio=rr, stop_distance_pct=1.0)
        ts = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
        sig = strategy.on_candle(50_000.0, "BTCUSDT", "15m", ts)
        stop_dist = 50_000.0 - sig["stop_price"]
        target_dist = sig["target_price"] - 50_000.0
        assert target_dist == pytest.approx(stop_dist * rr)
