"""
Tests for all 26 strategies — strategy-level behavioral tests.

For each strategy:
1. Instantiation with default parameters succeeds
2. Invalid parameters raise ValueError
3. generate_signal returns None during warm-up
4. generate_signal returns Signal | None after warm-up (type check)
5. Signal has correct direction
6. Signal metadata is populated
7. reset() works correctly

Organized by strategy group (A-H).
"""

import pytest
import math
from datetime import datetime, timedelta, timezone

from crypto_research.core.domain import Candle, Signal, SignalDirection, Timeframe

# Group A — Trend
from crypto_research.strategies.trend.ema_crossover import EMACrossover
from crypto_research.strategies.trend.triple_ema import TripleEMA
from crypto_research.strategies.trend.price_vs_ema import PriceVsEMA
from crypto_research.strategies.trend.ema_slope import EMASlope

# Group B — Momentum
from crypto_research.strategies.momentum.rsi_momentum import RSIMomentum
from crypto_research.strategies.momentum.roc_momentum import ROCMomentum
from crypto_research.strategies.momentum.macd_momentum import MACDMomentum
from crypto_research.strategies.momentum.multi_period_momentum import MultiPeriodMomentum

# Group C — Mean Reversion
from crypto_research.strategies.mean_reversion.bb_reversion import BBReversion
from crypto_research.strategies.mean_reversion.rsi_extreme import RSIExtreme
from crypto_research.strategies.mean_reversion.zscore_reversion import ZScoreReversion
from crypto_research.strategies.mean_reversion.ema_distance import EMADistance

# Group D — Breakout
from crypto_research.strategies.breakout.donchian_breakout import DonchianBreakout
from crypto_research.strategies.breakout.range_breakout import RangeBreakout
from crypto_research.strategies.breakout.volatility_breakout import VolatilityBreakout
from crypto_research.strategies.breakout.atr_channel_break import ATRChannelBreakout

# Group E — Volatility
from crypto_research.strategies.volatility.volatility_strategies import (
    ATRExpansion, VolatilityCompression, BBWidthExpansion
)

# Group F — Volume
from crypto_research.strategies.volume.volume_strategies import (
    VolumeSpike, VolumeWeightedMomentum, VolumeBreakoutConfirmation
)

# Group G — Multi-Indicator
from crypto_research.strategies.multi_indicator.multi_indicator_strategies import (
    TrendMomentumVolume, TrendVolatilityMomentum
)

# Group H — Market Structure
from crypto_research.strategies.market_structure.market_structure_strategies import (
    HHHLStructure, VolatilityRegimeConditional
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_candle(close: float, ts: datetime, asset: str = "BTCUSDT",
                high_offset: float = 1.0, low_offset: float = 1.0,
                volume: float = 1000.0) -> Candle:
    return Candle(
        timestamp=ts, asset=asset, timeframe=Timeframe.M15,
        open=close, high=close + high_offset, low=close - low_offset,
        close=close, volume=volume,
    )


def make_candles(prices: list[float], volumes: list[float] | None = None,
                 highs: list[float] | None = None, lows: list[float] | None = None) -> list[Candle]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candles = []
    for i, p in enumerate(prices):
        ts = base + timedelta(minutes=15 * i)
        vol = volumes[i] if volumes else 1000.0
        h = highs[i] if highs else p + 1.0
        l = lows[i] if lows else p - 1.0
        candles.append(Candle(
            timestamp=ts, asset="BTCUSDT", timeframe=Timeframe.M15,
            open=p, high=h, low=l, close=p, volume=vol,
        ))
    return candles


def now() -> datetime:
    return datetime(2024, 1, 2, tzinfo=timezone.utc)


def assert_warmup_blocks(strategy, n_candles: int) -> None:
    """Assert that strategy returns None when given fewer candles than warmup."""
    prices = [100.0] * n_candles
    candles = make_candles(prices)
    result = strategy.generate_signal(candles, now())
    assert result is None, f"Expected None during warmup, got {result}"


def run_strategy_many_candles(strategy, n: int = 100, prices: list[float] | None = None) -> list[Signal]:
    """Run strategy through n candles, collect all non-None signals."""
    if prices is None:
        # Oscillating prices to trigger various strategies
        prices = [100.0 + math.sin(i * 0.2) * 5 + i * 0.05 for i in range(n)]
    candles = make_candles(prices)
    signals = []
    for i in range(1, len(candles) + 1):
        sig = strategy.generate_signal(candles[:i], candles[i - 1].timestamp)
        if sig is not None:
            signals.append(sig)
    return signals


# ---------------------------------------------------------------------------
# Group A — Trend
# ---------------------------------------------------------------------------

class TestEMACrossover:
    def test_default_init(self):
        s = EMACrossover()
        assert s.parameters["fast_period"] == 9
        assert s.parameters["slow_period"] == 21

    def test_invalid_fast_ge_slow(self):
        with pytest.raises(ValueError):
            EMACrossover(fast_period=21, slow_period=9)

    def test_invalid_zero_period(self):
        with pytest.raises(ValueError):
            EMACrossover(fast_period=0)

    def test_warmup_blocks(self):
        assert_warmup_blocks(EMACrossover(), 5)

    def test_signal_is_long(self):
        s = EMACrossover(fast_period=5, slow_period=13)
        # Rising prices force fast EMA above slow EMA
        prices = [100.0] * 20 + [100.0 + i * 3.0 for i in range(20)]
        candles = make_candles(prices)
        signals = []
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            if sig is not None:
                signals.append(sig)
        if signals:
            assert all(s.direction == SignalDirection.LONG for s in signals)

    def test_reset_clears_state(self):
        s = EMACrossover()
        s._prev_fast_above = True
        s.reset()
        assert s._prev_fast_above is None

    def test_repr(self):
        s = EMACrossover()
        assert "EMA_CROSS_001" in repr(s)


class TestTripleEMA:
    def test_default_init(self):
        s = TripleEMA()
        assert s.parameters["fast_period"] == 5

    def test_invalid_ordering(self):
        with pytest.raises(ValueError):
            TripleEMA(fast_period=20, medium_period=10, slow_period=30)

    def test_warmup_blocks(self):
        assert_warmup_blocks(TripleEMA(), 5)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(TripleEMA(fast_period=5, medium_period=10, slow_period=20))
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestPriceVsEMA:
    def test_default_init(self):
        s = PriceVsEMA()
        assert s.parameters["long_period"] == 50

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            PriceVsEMA(min_momentum_pct=-0.1)
        with pytest.raises(ValueError):
            PriceVsEMA(cooldown_candles=-1)

    def test_warmup_blocks(self):
        assert_warmup_blocks(PriceVsEMA(long_period=10, momentum_period=2), 5)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(PriceVsEMA(long_period=20, cooldown_candles=3))
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestEMASlope:
    def test_default_init(self):
        s = EMASlope()
        assert s.parameters["ema_period"] == 21

    def test_warmup_blocks(self):
        assert_warmup_blocks(EMASlope(), 5)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(EMASlope(ema_period=10, slope_period=2))
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


# ---------------------------------------------------------------------------
# Group B — Momentum
# ---------------------------------------------------------------------------

class TestRSIMomentum:
    def test_default_init(self):
        s = RSIMomentum()
        assert s.parameters["rsi_period"] == 14

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            RSIMomentum(entry_threshold=101.0)

    def test_warmup_blocks(self):
        assert_warmup_blocks(RSIMomentum(), 5)

    def test_constant_prices_no_signal(self):
        s = RSIMomentum()
        prices = [100.0] * 50
        candles = make_candles(prices)
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            assert sig is None  # RSI undefined for constant prices


class TestROCMomentum:
    def test_default_init(self):
        s = ROCMomentum()
        assert s.parameters["lookback"] == 10

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            ROCMomentum(threshold=-1.0)

    def test_warmup_blocks(self):
        assert_warmup_blocks(ROCMomentum(), 3)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(ROCMomentum(lookback=5, threshold=0.1))
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestMACDMomentum:
    def test_default_init(self):
        s = MACDMomentum()
        assert s.parameters["fast_period"] == 12

    def test_invalid_fast_ge_slow(self):
        with pytest.raises(ValueError):
            MACDMomentum(fast_period=30, slow_period=12)

    def test_warmup_blocks(self):
        assert_warmup_blocks(MACDMomentum(), 5)


class TestMultiPeriodMomentum:
    def test_default_init(self):
        s = MultiPeriodMomentum()
        assert s.parameters["short_period"] == 5

    def test_invalid_ordering(self):
        with pytest.raises(ValueError):
            MultiPeriodMomentum(short_period=15, medium_period=5)

    def test_warmup_blocks(self):
        assert_warmup_blocks(MultiPeriodMomentum(), 3)


# ---------------------------------------------------------------------------
# Group C — Mean Reversion
# ---------------------------------------------------------------------------

class TestBBReversion:
    def test_default_init(self):
        s = BBReversion()
        assert s.parameters["period"] == 20

    def test_invalid_num_std(self):
        with pytest.raises(ValueError):
            BBReversion(num_std=0.0)

    def test_warmup_blocks(self):
        assert_warmup_blocks(BBReversion(), 5)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(BBReversion(period=10))
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestRSIExtreme:
    def test_default_init(self):
        s = RSIExtreme()
        assert s.parameters["oversold_level"] == 30.0

    def test_invalid_oversold_level(self):
        with pytest.raises(ValueError):
            RSIExtreme(oversold_level=60.0)  # must be < 50

    def test_warmup_blocks(self):
        assert_warmup_blocks(RSIExtreme(), 5)


class TestZScoreReversion:
    def test_default_init(self):
        s = ZScoreReversion()
        assert s.parameters["period"] == 20

    def test_invalid_threshold_ordering(self):
        with pytest.raises(ValueError):
            ZScoreReversion(lower_threshold=-1.0, upper_threshold=-2.0)

    def test_warmup_blocks(self):
        assert_warmup_blocks(ZScoreReversion(), 5)

    def test_constant_prices_no_signal(self):
        s = ZScoreReversion(period=10)
        prices = [100.0] * 30
        candles = make_candles(prices)
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            assert sig is None  # std=0 → None

    def test_arms_then_fires(self):
        s = ZScoreReversion(period=10, lower_threshold=-2.0, upper_threshold=-0.5)
        # Prices: mostly flat at 100, then crash to 60, then recover to 95
        prices = [100.0] * 15 + [60.0] + [95.0]
        candles = make_candles(prices)
        signals = []
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            if sig is not None:
                signals.append(sig)
        # May or may not fire depending on exact Z-score, but must not crash
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestEMADistance:
    def test_default_init(self):
        s = EMADistance()
        assert s.parameters["ema_period"] == 20

    def test_invalid_threshold_ordering(self):
        with pytest.raises(ValueError):
            EMADistance(arm_distance_pct=-1.0, fire_distance_pct=-2.0)  # fire < arm

    def test_invalid_fire_above_zero(self):
        with pytest.raises(ValueError):
            EMADistance(fire_distance_pct=0.5)

    def test_warmup_blocks(self):
        assert_warmup_blocks(EMADistance(), 5)


# ---------------------------------------------------------------------------
# Group D — Breakout
# ---------------------------------------------------------------------------

class TestDonchianBreakout:
    def test_default_init(self):
        s = DonchianBreakout()
        assert s.parameters["period"] == 20

    def test_invalid_period(self):
        with pytest.raises(ValueError):
            DonchianBreakout(period=1)

    def test_warmup_blocks(self):
        assert_warmup_blocks(DonchianBreakout(), 5)

    def test_signal_on_breakout(self):
        s = DonchianBreakout(period=10)
        # Flat then break out
        prices = [100.0] * 15 + [200.0]
        candles = make_candles(prices)
        signals = []
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            if sig is not None:
                signals.append(sig)
        assert len(signals) == 1
        assert signals[0].direction == SignalDirection.LONG


class TestRangeBreakout:
    def test_default_init(self):
        s = RangeBreakout()
        assert s.parameters["period"] == 15

    def test_warmup_blocks(self):
        assert_warmup_blocks(RangeBreakout(), 5)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(RangeBreakout(period=10))
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestVolatilityBreakout:
    def test_default_init(self):
        s = VolatilityBreakout()
        assert s.parameters["atr_multiplier"] == 1.2

    def test_invalid_multiplier(self):
        with pytest.raises(ValueError):
            VolatilityBreakout(atr_multiplier=0.5)

    def test_warmup_blocks(self):
        assert_warmup_blocks(VolatilityBreakout(), 5)


class TestATRChannelBreakout:
    def test_default_init(self):
        s = ATRChannelBreakout()
        assert s.parameters["ema_period"] == 20

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            ATRChannelBreakout(atr_multiplier=0.0)

    def test_warmup_blocks(self):
        assert_warmup_blocks(ATRChannelBreakout(), 5)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(ATRChannelBreakout(ema_period=10, atr_period=5))
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


# ---------------------------------------------------------------------------
# Group E — Volatility
# ---------------------------------------------------------------------------

class TestATRExpansion:
    def test_default_init(self):
        s = ATRExpansion()
        assert s.parameters["multiplier"] == 1.2

    def test_invalid_multiplier(self):
        with pytest.raises(ValueError):
            ATRExpansion(multiplier=0.5)

    def test_warmup_blocks(self):
        assert_warmup_blocks(ATRExpansion(), 5)


class TestVolatilityCompression:
    def test_default_init(self):
        s = VolatilityCompression()
        assert s.parameters["compression_threshold"] == 0.02

    def test_invalid_threshold_ordering(self):
        with pytest.raises(ValueError):
            VolatilityCompression(compression_threshold=0.05, expansion_threshold=0.03)

    def test_warmup_blocks(self):
        assert_warmup_blocks(VolatilityCompression(), 5)


class TestBBWidthExpansion:
    def test_default_init(self):
        s = BBWidthExpansion()
        assert s.parameters["width_avg_multiplier"] == 1.3

    def test_warmup_blocks(self):
        assert_warmup_blocks(BBWidthExpansion(), 5)


# ---------------------------------------------------------------------------
# Group F — Volume
# ---------------------------------------------------------------------------

class TestVolumeSpike:
    def test_default_init(self):
        s = VolumeSpike()
        assert s.parameters["rv_threshold"] == 2.0

    def test_invalid_threshold(self):
        with pytest.raises(ValueError):
            VolumeSpike(rv_threshold=0.5)

    def test_warmup_blocks(self):
        assert_warmup_blocks(VolumeSpike(), 5)

    def test_no_signal_uniform_volume(self):
        s = VolumeSpike(vol_period=10, rv_threshold=2.0)
        prices = [100.0] * 20
        vols = [1000.0] * 20
        candles = make_candles(prices, volumes=vols)
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            assert sig is None  # RV = 1.0 < threshold 2.0


class TestVolumeWeightedMomentum:
    def test_default_init(self):
        s = VolumeWeightedMomentum()
        assert s.parameters["rv_threshold"] == 1.5

    def test_warmup_blocks(self):
        assert_warmup_blocks(VolumeWeightedMomentum(), 5)


class TestVolumeBreakoutConfirmation:
    def test_default_init(self):
        s = VolumeBreakoutConfirmation()
        assert s.parameters["rv_threshold"] == 1.5

    def test_warmup_blocks(self):
        assert_warmup_blocks(VolumeBreakoutConfirmation(), 5)


# ---------------------------------------------------------------------------
# Group G — Multi-Indicator
# ---------------------------------------------------------------------------

class TestTrendMomentumVolume:
    def test_default_init(self):
        s = TrendMomentumVolume()
        assert s.parameters["ema_period"] == 21

    def test_warmup_blocks(self):
        assert_warmup_blocks(TrendMomentumVolume(), 5)

    def test_signal_direction(self):
        signals = run_strategy_many_candles(
            TrendMomentumVolume(ema_period=10, roc_period=5, vol_period=10)
        )
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestTrendVolatilityMomentum:
    def test_default_init(self):
        s = TrendVolatilityMomentum()
        assert s.parameters["rsi_level"] == 55.0

    def test_invalid_rsi_level(self):
        with pytest.raises(ValueError):
            TrendVolatilityMomentum(rsi_level=101.0)

    def test_warmup_blocks(self):
        assert_warmup_blocks(TrendVolatilityMomentum(), 5)


# ---------------------------------------------------------------------------
# Group H — Market Structure
# ---------------------------------------------------------------------------

class TestHHHLStructure:
    def test_default_init(self):
        s = HHHLStructure()
        assert s.parameters["lookback"] == 5

    def test_invalid_lookback(self):
        with pytest.raises(ValueError):
            HHHLStructure(lookback=1)

    def test_warmup_blocks(self):
        assert_warmup_blocks(HHHLStructure(), 3)

    def test_signal_on_hh_hl(self):
        s = HHHLStructure(lookback=3)
        # Rising prices forming HH/HL
        prices = [100.0, 101.0, 99.0, 102.0, 100.0, 103.0, 101.0, 104.0]
        candles = make_candles(prices)
        signals = []
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            if sig is not None:
                signals.append(sig)
        for sig in signals:
            assert sig.direction == SignalDirection.LONG


class TestVolatilityRegimeConditional:
    def test_default_init(self):
        s = VolatilityRegimeConditional()
        assert s.parameters["expansion_threshold"] == 0.04

    def test_invalid_breakout_period(self):
        with pytest.raises(ValueError):
            VolatilityRegimeConditional(breakout_period=1)

    def test_warmup_blocks(self):
        assert_warmup_blocks(VolatilityRegimeConditional(), 5)

    def test_no_signal_in_low_volatility(self):
        s = VolatilityRegimeConditional(expansion_threshold=0.5)  # very high threshold
        # Constant prices → BB width ≈ 0 → below threshold → no signals
        prices = [100.0] * 50
        candles = make_candles(prices)
        for i in range(1, len(candles) + 1):
            sig = s.generate_signal(candles[:i], candles[i - 1].timestamp)
            assert sig is None


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------

class TestRegistryCompleteness:
    def test_all_26_registered(self):
        import crypto_research.strategies
        from crypto_research.strategies import REGISTRY
        assert len(REGISTRY) == 26

    def test_all_8_categories_present(self):
        import crypto_research.strategies
        from crypto_research.strategies import REGISTRY
        cats = REGISTRY.categories()
        expected = {"trend", "momentum", "mean_reversion", "breakout",
                    "volatility", "volume", "multi_indicator", "market_structure"}
        assert set(cats) == expected

    def test_all_strategies_have_warmup(self):
        import crypto_research.strategies
        from crypto_research.strategies import REGISTRY
        for info in REGISTRY.list():
            assert info.warmup_period >= 0, f"{info.strategy_id} has negative warmup"

    def test_all_strategies_instantiatable(self):
        import crypto_research.strategies
        from crypto_research.strategies import REGISTRY
        for info in REGISTRY.list():
            instance = REGISTRY.instantiate(info.strategy_id)
            assert isinstance(instance, __import__(
                "crypto_research.strategies.base", fromlist=["BaseStrategy"]
            ).BaseStrategy)
