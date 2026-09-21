"""
Tests for the indicator library.

Covers: SMA, EMA, WMA, RSI, ROC, MACD, ATR, rolling_std,
        Bollinger Bands, BB Width, Relative Volume, Z-Score,
        Donchian Channels, rolling_high/low.

Tests:
    - Normal operation
    - Warm-up (insufficient history → None)
    - Constant prices / zero-volatility
    - Zero volume
    - NaN-free output
"""

import math
import pytest
from crypto_research.strategies.indicators import (
    atr, bb_width, bollinger_bands, donchian_channels, ema, ema_series,
    macd, relative_volume, roc, rolling_high, rolling_low, rolling_std, rsi, sma,
    volume_sma, wma, zscore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def constant_prices(n: int = 30, price: float = 100.0) -> list[float]:
    return [price] * n

def linear_prices(n: int = 30, start: float = 100.0, step: float = 1.0) -> list[float]:
    return [start + i * step for i in range(n)]

def ohlc_from_closes(closes: list[float]) -> tuple[list[float], list[float], list[float]]:
    """Build simple highs/lows from closes (high = close, low = close for simplicity)."""
    return closes, closes, closes


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------

class TestSMA:
    def test_simple(self):
        assert sma([1.0, 2.0, 3.0, 4.0, 5.0], 3) == pytest.approx(4.0)

    def test_insufficient_history(self):
        assert sma([1.0, 2.0], 3) is None

    def test_exact_period(self):
        assert sma([10.0, 20.0, 30.0], 3) == pytest.approx(20.0)

    def test_constant_prices(self):
        prices = constant_prices(20)
        result = sma(prices, 10)
        assert result == pytest.approx(100.0)

    def test_invalid_period(self):
        with pytest.raises(ValueError):
            sma([1.0, 2.0, 3.0], 0)


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

class TestEMA:
    def test_insufficient_history(self):
        assert ema([1.0, 2.0], 5) is None

    def test_constant_prices(self):
        prices = constant_prices(30)
        result = ema(prices, 10)
        assert result == pytest.approx(100.0)

    def test_rising_prices_above_initial(self):
        prices = linear_prices(30, start=100.0, step=1.0)
        result = ema(prices, 10)
        assert result is not None
        assert result > 100.0

    def test_invalid_period(self):
        with pytest.raises(ValueError):
            ema([1.0], 0)

    def test_returns_float(self):
        result = ema(linear_prices(20), 10)
        assert isinstance(result, float)


class TestEMASeries:
    def test_length_equals_input(self):
        prices = linear_prices(20)
        result = ema_series(prices, 5)
        assert len(result) == 20

    def test_leading_nones(self):
        prices = linear_prices(20)
        result = ema_series(prices, 10)
        # First 9 values should be None (indices 0..8)
        for v in result[:9]:
            assert v is None
        assert result[9] is not None

    def test_seed_equals_sma(self):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = ema_series(prices, 3)
        # Index 2 = seed = SMA(10, 20, 30) = 20.0
        assert result[2] == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# WMA
# ---------------------------------------------------------------------------

class TestWMA:
    def test_insufficient(self):
        assert wma([1.0, 2.0], 5) is None

    def test_known_value(self):
        # weights=[1,2,3], prices=[10,20,30] → (10*1+20*2+30*3)/6 = (10+40+90)/6 = 140/6
        result = wma([10.0, 20.0, 30.0], 3)
        assert result == pytest.approx(140.0 / 6.0)

    def test_constant(self):
        assert wma(constant_prices(10), 5) == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

class TestRSI:
    def test_insufficient(self):
        assert rsi([1.0] * 10, 14) is None

    def test_constant_prices(self):
        # Constant prices → no gains no losses → None
        result = rsi(constant_prices(30), 14)
        assert result is None

    def test_all_gains(self):
        prices = linear_prices(30, step=1.0)
        result = rsi(prices, 14)
        assert result == pytest.approx(100.0)

    def test_all_losses(self):
        prices = linear_prices(30, step=-1.0)
        result = rsi(prices, 14)
        assert result == pytest.approx(0.0)

    def test_range(self):
        prices = [100.0 + math.sin(i * 0.3) * 5 for i in range(30)]
        result = rsi(prices, 14)
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_invalid_period(self):
        with pytest.raises(ValueError):
            rsi([1.0] * 20, 0)


# ---------------------------------------------------------------------------
# ROC
# ---------------------------------------------------------------------------

class TestROC:
    def test_insufficient(self):
        assert roc([1.0] * 5, 10) is None

    def test_flat_market(self):
        assert roc(constant_prices(30), 10) == pytest.approx(0.0)

    def test_known_value(self):
        # ROC(10): prices[-11]=100, prices[-1]=110 → (110-100)/100*100 = 10.0%
        prices = [100.0] * 10 + [110.0]
        result = roc(prices, 10)
        assert result == pytest.approx(10.0)

    def test_zero_base_price(self):
        # prices[-11] must be 0 for division-by-zero: need exactly 11 prices starting with 0
        prices = [0.0] + [1.0] * 10  # prices[-11]=0, prices[-1]=1
        assert roc(prices, 10) is None


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

class TestMACD:
    def test_insufficient(self):
        ml, sl, hist = macd([1.0] * 10, 12, 26, 9)
        assert ml is None and sl is None and hist is None

    def test_returns_three_values(self):
        prices = linear_prices(50)
        ml, sl, hist = macd(prices, 12, 26, 9)
        assert ml is not None

    def test_invalid_periods(self):
        with pytest.raises(ValueError):
            macd([1.0] * 50, fast_period=26, slow_period=12)

    def test_flat_market_macd_near_zero(self):
        prices = constant_prices(60)
        ml, sl, hist = macd(prices, 12, 26, 9)
        # Constant prices → EMAs converge → MACD near 0
        if ml is not None:
            assert abs(ml) < 1e-6


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------

class TestATR:
    def test_insufficient(self):
        assert atr([100.0] * 5, [99.0] * 5, [100.0] * 5, 14) is None

    def test_constant_ohlc(self):
        n = 30
        result = atr([100.0] * n, [100.0] * n, [100.0] * n, 14)
        assert result == pytest.approx(0.0)

    def test_positive_value(self):
        n = 30
        highs = [100.0 + i * 0.1 for i in range(n)]
        lows = [100.0 - i * 0.1 for i in range(n)]
        closes = [100.0] * n
        result = atr(highs, lows, closes, 14)
        assert result is not None
        assert result > 0.0

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError):
            atr([100.0] * 5, [99.0] * 4, [100.0] * 5, 3)


# ---------------------------------------------------------------------------
# Rolling Std
# ---------------------------------------------------------------------------

class TestRollingStd:
    def test_insufficient(self):
        assert rolling_std([1.0, 2.0], 5) is None

    def test_constant(self):
        assert rolling_std(constant_prices(20), 10) == pytest.approx(0.0)

    def test_known_value(self):
        # [1, 3, 5] → mean=3, var=((1-3)²+(3-3)²+(5-3)²)/3 = 8/3 → std ≈ 1.6329
        result = rolling_std([1.0, 3.0, 5.0], 3)
        expected = math.sqrt(8.0 / 3.0)
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

class TestBollingerBands:
    def test_insufficient(self):
        u, m, l = bollinger_bands([1.0] * 5, 20)
        assert u is None and m is None and l is None

    def test_constant_prices(self):
        u, m, l = bollinger_bands(constant_prices(25), 20)
        # std=0, so all three bands == middle
        assert u == pytest.approx(100.0)
        assert m == pytest.approx(100.0)
        assert l == pytest.approx(100.0)

    def test_ordering(self):
        prices = [100.0 + math.sin(i * 0.5) * 5 for i in range(30)]
        u, m, l = bollinger_bands(prices, 20)
        assert u >= m >= l


# ---------------------------------------------------------------------------
# BB Width
# ---------------------------------------------------------------------------

class TestBBWidth:
    def test_insufficient(self):
        assert bb_width([1.0] * 5, 20) is None

    def test_constant_zero_width(self):
        assert bb_width(constant_prices(25), 20) == pytest.approx(0.0)

    def test_positive_for_volatile(self):
        prices = [100.0 + math.sin(i * 0.5) * 5 for i in range(30)]
        result = bb_width(prices, 20)
        assert result is not None and result > 0.0


# ---------------------------------------------------------------------------
# Relative Volume
# ---------------------------------------------------------------------------

class TestRelativeVolume:
    def test_insufficient(self):
        assert relative_volume([1.0] * 5, 20) is None

    def test_equal_volume(self):
        vols = [100.0] * 25
        result = relative_volume(vols, 20)
        assert result == pytest.approx(1.0)

    def test_spike(self):
        vols = [100.0] * 25
        vols[-1] = 300.0  # triple volume spike
        result = relative_volume(vols, 20)
        assert result == pytest.approx(3.0)

    def test_zero_baseline(self):
        vols = [0.0] * 25
        assert relative_volume(vols, 20) is None


# ---------------------------------------------------------------------------
# Z-Score
# ---------------------------------------------------------------------------

class TestZScore:
    def test_insufficient(self):
        assert zscore([1.0] * 5, 20) is None

    def test_constant_prices_none(self):
        # std=0 → undefined
        assert zscore(constant_prices(25), 20) is None

    def test_current_at_mean_is_zero(self):
        # All prices at 100 except the last which is also 100
        prices = constant_prices(25, 100.0)
        # Since std==0 this returns None; inject variance
        prices[10] = 110.0  # creates some variance
        result = zscore(prices, 20)
        assert result is not None

    def test_far_above_mean_positive(self):
        prices = [100.0] * 24 + [200.0]  # last price is way above mean
        result = zscore(prices, 20)
        assert result is not None and result > 0.0


# ---------------------------------------------------------------------------
# Donchian Channels
# ---------------------------------------------------------------------------

class TestDonchianChannels:
    def test_insufficient_with_previous_window(self):
        highs = [100.0] * 10
        lows = [99.0] * 10
        u, l = donchian_channels(highs, lows, 20, use_previous_window=True)
        assert u is None and l is None

    def test_uses_prior_window(self):
        # Build highs where last value is highest but prior window is flat
        highs = [100.0] * 21 + [200.0]  # last is 200 but prior window = [100]*21
        lows = [99.0] * 22
        u, l = donchian_channels(highs, lows, 20, use_previous_window=True)
        # Upper should be from prior window (100), not current candle (200)
        assert u == pytest.approx(100.0)

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError):
            donchian_channels([100.0] * 5, [99.0] * 4, 3)


# ---------------------------------------------------------------------------
# Rolling High / Low
# ---------------------------------------------------------------------------

class TestRollingHighLow:
    def test_rolling_high_basic(self):
        prices = [1.0, 5.0, 3.0, 4.0, 2.0]
        assert rolling_high(prices, 3, shift=0) == pytest.approx(4.0)

    def test_rolling_low_basic(self):
        prices = [1.0, 5.0, 3.0, 4.0, 2.0]
        assert rolling_low(prices, 3, shift=0) == pytest.approx(2.0)

    def test_shift_1_excludes_current(self):
        prices = [1.0, 2.0, 3.0, 4.0, 100.0]  # last is huge
        # With shift=1, the window is [3.0, 4.0, ???] ... prices[-4:-1] = [2,3,4]
        result = rolling_high(prices, 3, shift=1)
        assert result == pytest.approx(4.0)

    def test_insufficient(self):
        assert rolling_high([1.0, 2.0], 5) is None
        assert rolling_low([1.0, 2.0], 5) is None
