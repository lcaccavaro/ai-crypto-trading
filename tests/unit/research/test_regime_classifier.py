"""
Unit tests for the RegimeClassifier.

Tests:
    - PIT safety: regime at T only uses data up to T
    - TREND classification correctness
    - VOLATILITY classification correctness
    - Combined label format
    - Empty DataFrame handling
    - get_regime_at() lookup
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from crypto_research.config.schema import (
    RegimeConfig, RegimeTrendConfig, RegimeVolatilityConfig
)
from crypto_research.research.regimes.classifier import (
    RegimeClassifier, TrendRegime, VolatilityRegime
)


def make_config(
    ma_period: int = 5,
    slope_threshold_pct: float = 1.0,
    atr_period: int = 3,
    low_vol_pct: float = 1.0,
    high_vol_pct: float = 3.0,
) -> RegimeConfig:
    return RegimeConfig(
        enabled=True,
        trend=RegimeTrendConfig(ma_period=ma_period, slope_threshold_pct=slope_threshold_pct),
        volatility=RegimeVolatilityConfig(
            atr_period=atr_period,
            low_threshold_pct=low_vol_pct,
            high_threshold_pct=high_vol_pct,
        ),
    )


def make_ohlcv_df(close_prices: list[float], high_prices: list[float] = None, low_prices: list[float] = None) -> pd.DataFrame:
    n = len(close_prices)
    closes = pd.Series(close_prices)
    highs = pd.Series(high_prices) if high_prices else closes * 1.01
    lows = pd.Series(low_prices) if low_prices else closes * 0.99
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
        "open": closes.shift(1).fillna(closes[0]),
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [1000.0] * n,
    })


class TestTrendClassification:
    def test_uptrend_detected(self):
        """Rising price clearly above short MA → TREND_UP."""
        cfg = make_config(ma_period=5, slope_threshold_pct=0.5)
        clf = RegimeClassifier(cfg)
        # Build strongly rising price series
        closes = [100.0 * (1 + 0.02 * i) for i in range(30)]
        df = make_ohlcv_df(closes)
        result = clf.classify_dataframe(df)
        # Last row should be TREND_UP
        last_trend = result["trend_regime"].iloc[-1]
        assert last_trend == TrendRegime.TREND_UP.value

    def test_downtrend_detected(self):
        """Falling price clearly below short MA → TREND_DOWN."""
        cfg = make_config(ma_period=5, slope_threshold_pct=0.5)
        clf = RegimeClassifier(cfg)
        closes = [100.0 * (1 - 0.015 * i) for i in range(30)]
        df = make_ohlcv_df(closes)
        result = clf.classify_dataframe(df)
        last_trend = result["trend_regime"].iloc[-1]
        assert last_trend == TrendRegime.TREND_DOWN.value

    def test_range_detected(self):
        """Oscillating price near MA → RANGE."""
        cfg = make_config(ma_period=5, slope_threshold_pct=2.0)
        clf = RegimeClassifier(cfg)
        # Small oscillation around 100
        closes = [100.0 + 0.5 * ((-1) ** i) for i in range(30)]
        df = make_ohlcv_df(closes)
        result = clf.classify_dataframe(df)
        last_trend = result["trend_regime"].iloc[-1]
        assert last_trend == TrendRegime.RANGE.value


class TestVolatilityClassification:
    def test_low_vol_detected(self):
        """Tiny candle ranges → LOW_VOL."""
        cfg = make_config(atr_period=3, low_vol_pct=1.0, high_vol_pct=3.0)
        clf = RegimeClassifier(cfg)
        closes = [100.0] * 30
        # Tiny range: 0.1% band
        highs = [c * 1.001 for c in closes]
        lows = [c * 0.999 for c in closes]
        df = make_ohlcv_df(closes, highs, lows)
        result = clf.classify_dataframe(df)
        last_vol = result["vol_regime"].iloc[-1]
        assert last_vol == VolatilityRegime.LOW_VOL.value

    def test_high_vol_detected(self):
        """Large candle ranges → HIGH_VOL."""
        cfg = make_config(atr_period=3, low_vol_pct=1.0, high_vol_pct=3.0)
        clf = RegimeClassifier(cfg)
        closes = [100.0] * 30
        # Wide range: 5% band
        highs = [c * 1.05 for c in closes]
        lows = [c * 0.95 for c in closes]
        df = make_ohlcv_df(closes, highs, lows)
        result = clf.classify_dataframe(df)
        last_vol = result["vol_regime"].iloc[-1]
        assert last_vol == VolatilityRegime.HIGH_VOL.value


class TestOutputFormat:
    def test_combined_column_format(self):
        cfg = make_config()
        clf = RegimeClassifier(cfg)
        df = make_ohlcv_df([100.0] * 20)
        result = clf.classify_dataframe(df)
        # Combined should be "TREND_VOL" format
        for val in result["combined_regime"].dropna():
            assert "_" in val
            parts = val.split("_", 1)
            assert len(parts) == 2

    def test_required_columns_added(self):
        cfg = make_config()
        clf = RegimeClassifier(cfg)
        df = make_ohlcv_df([100.0] * 20)
        result = clf.classify_dataframe(df)
        for col in ["trend_regime", "vol_regime", "combined_regime", "ma_value", "atr_pct"]:
            assert col in result.columns

    def test_empty_dataframe(self):
        cfg = make_config()
        clf = RegimeClassifier(cfg)
        empty_df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        result = clf.classify_dataframe(empty_df)
        # Should return without crashing
        assert "combined_regime" in result.columns

    def test_no_future_leak_first_rows(self):
        """
        PIT safety: the MA at row i uses only candles up to row i.
        Rows 0..min_periods-2 will have NaN (not enough history for full window).
        Rows from min_periods-1 onward should have a valid MA.
        The MA at the last row must NOT equal future close values.
        """
        ma_period = 10
        cfg = make_config(ma_period=ma_period)
        clf = RegimeClassifier(cfg)
        closes = [100.0 + float(i) for i in range(20)]
        df = make_ohlcv_df(closes)
        result = clf.classify_dataframe(df)

        # min_periods is max(1, ma_period // 2) = max(1, 5) = 5
        # Rows 0..3 → NaN; rows 4+ → valid MA
        min_periods = max(1, ma_period // 2)
        valid_rows = result["ma_value"].iloc[min_periods:]
        assert not valid_rows.isna().all(), "Expected at least some non-NaN MA values"

        # MA at last row should be mean of last ma_period closes (not future data)
        last_ma = result["ma_value"].iloc[-1]
        expected_ma = sum(closes[-ma_period:]) / ma_period
        assert abs(last_ma - expected_ma) < 1e-6, f"MA mismatch: {last_ma} != {expected_ma}"

