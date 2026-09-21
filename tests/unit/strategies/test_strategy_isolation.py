"""
State isolation tests — critical guarantee for all strategies.

Tests verify that:
1. Two instances of the same strategy do NOT share state.
2. reset() returns a strategy to its initial state.
3. Instance state from one symbol does not bleed into another.
4. Strategy instance IDs are unique per (strategy_id, symbol, timeframe, params).

These are the most important tests in the suite because state leakage would
produce look-ahead bias or corrupted signals.
"""

import pytest
from datetime import datetime, timedelta, timezone

from crypto_research.core.domain import Candle, Timeframe
from crypto_research.strategies.context import StrategyInstance
from crypto_research.strategies.trend.ema_crossover import EMACrossover
from crypto_research.strategies.mean_reversion.zscore_reversion import ZScoreReversion
from crypto_research.strategies.momentum.rsi_momentum import RSIMomentum
from crypto_research.strategies.breakout.donchian_breakout import DonchianBreakout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candle(close: float, ts: datetime, asset: str = "BTCUSDT") -> Candle:
    return Candle(
        timestamp=ts,
        asset=asset,
        timeframe=Timeframe.M15,
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=1000.0,
    )


def make_candles(prices: list[float], asset: str = "BTCUSDT") -> list[Candle]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [make_candle(p, base + timedelta(minutes=15 * i), asset) for i, p in enumerate(prices)]


# Prices that create a crossover in EMA_CROSS_001
def crossover_prices(n: int = 40) -> list[float]:
    # Start flat then rise sharply to create fast EMA crossing above slow EMA
    return [100.0] * 20 + [100.0 + i * 2.0 for i in range(n - 20)]


# ---------------------------------------------------------------------------
# State isolation: two instances of same strategy class
# ---------------------------------------------------------------------------

class TestStateIsolation:
    def test_two_instances_independent(self):
        """Two instances of EMACrossover must not share state."""
        strat_a = EMACrossover(fast_period=9, slow_period=21)
        strat_b = EMACrossover(fast_period=9, slow_period=21)

        prices = crossover_prices(40)
        candles_a = make_candles(prices, "BTCUSDT")
        candles_b = make_candles(prices, "ETHUSDT")

        ts = candles_a[-1].timestamp

        # Run strat_a through the full candle history
        for i in range(1, len(candles_a) + 1):
            strat_a.generate_signal(candles_a[:i], ts)

        # strat_b has had NO candles — its prev_fast_above should still be None
        assert strat_b._prev_fast_above is None

    def test_zscore_armed_state_not_shared(self):
        """Two ZScoreReversion instances must have independent armed state."""
        strat_1 = ZScoreReversion(period=10, lower_threshold=-2.0, upper_threshold=-0.5)
        strat_2 = ZScoreReversion(period=10, lower_threshold=-2.0, upper_threshold=-0.5)

        # Arm strat_1 by feeding a big downward price
        prices_down = [100.0] * 9 + [60.0]  # huge drop → very negative Z-score
        candles = make_candles(prices_down)
        ts = candles[-1].timestamp
        strat_1.generate_signal(candles, ts)

        # strat_2 must not be armed
        assert strat_2._armed is False

    def test_rsi_state_not_shared(self):
        """RSIMomentum instances must have independent _prev_rsi."""
        strat_1 = RSIMomentum(rsi_period=7, entry_threshold=55.0)
        strat_2 = RSIMomentum(rsi_period=7, entry_threshold=55.0)

        prices = [100.0 + i * 0.5 for i in range(20)]
        candles = make_candles(prices)
        ts = candles[-1].timestamp

        strat_1.generate_signal(candles, ts)

        # strat_2 prev_rsi should still be None
        assert strat_2._prev_rsi is None


# ---------------------------------------------------------------------------
# reset() tests
# ---------------------------------------------------------------------------

class TestReset:
    def test_ema_crossover_reset_clears_state(self):
        strat = EMACrossover(fast_period=9, slow_period=21)
        prices = crossover_prices(40)
        candles = make_candles(prices)
        ts = candles[-1].timestamp

        # Run partially
        for i in range(1, 30):
            strat.generate_signal(candles[:i], ts)

        # State should be set
        assert strat._prev_fast_above is not None

        # Reset
        strat.reset()
        assert strat._prev_fast_above is None

    def test_zscore_reset_clears_armed(self):
        strat = ZScoreReversion(period=10)

        # Arm it manually
        strat._armed = True
        strat.reset()
        assert strat._armed is False

    def test_donchian_reset_clears_state(self):
        strat = DonchianBreakout(period=10)
        strat._prev_above_channel = True
        strat.reset()
        assert strat._prev_above_channel is None


# ---------------------------------------------------------------------------
# StrategyInstance identity
# ---------------------------------------------------------------------------

class TestStrategyInstanceIdentity:
    def test_same_params_same_id(self):
        inst1 = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="BTCUSDT",
            timeframe="15m",
            version="1.0.0",
            parameters={"fast_period": 9, "slow_period": 21},
        )
        inst2 = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="BTCUSDT",
            timeframe="15m",
            version="1.0.0",
            parameters={"fast_period": 9, "slow_period": 21},
        )
        assert inst1.instance_id == inst2.instance_id

    def test_different_symbol_different_id(self):
        inst1 = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="BTCUSDT",
            timeframe="15m",
            version="1.0.0",
        )
        inst2 = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="ETHUSDT",
            timeframe="15m",
            version="1.0.0",
        )
        assert inst1.instance_id != inst2.instance_id

    def test_different_params_different_id(self):
        inst1 = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="BTCUSDT",
            timeframe="15m",
            version="1.0.0",
            parameters={"fast_period": 9},
        )
        inst2 = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="BTCUSDT",
            timeframe="15m",
            version="1.0.0",
            parameters={"fast_period": 12},
        )
        assert inst1.instance_id != inst2.instance_id

    def test_no_params_base_id_format(self):
        inst = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="BTCUSDT",
            timeframe="15m",
            version="1.0.0",
        )
        # Without params: format = EMA_CROSS_001__BTCUSDT__15m__v1.0.0
        assert inst.instance_id == "EMA_CROSS_001__BTCUSDT__15m__v1.0.0"

    def test_empty_strategy_id_raises(self):
        with pytest.raises(ValueError):
            StrategyInstance(strategy_id="", symbol="BTCUSDT", timeframe="15m", version="1.0.0")

    def test_str(self):
        inst = StrategyInstance(
            strategy_id="EMA_CROSS_001",
            symbol="BTCUSDT",
            timeframe="15m",
            version="1.0.0",
        )
        assert str(inst) == inst.instance_id
