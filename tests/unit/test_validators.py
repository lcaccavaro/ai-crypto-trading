"""
Unit tests for all 5 data validators (offline, no network).

Uses synthetic DataFrames to test each validator independently.
All synthetic data is clearly labeled as TEST FIXTURE — never presented
as real market data.
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from crypto_research.data.validators import (
    REQUIRED_COLUMNS,
    ValidationStatus,
    run_validation_pipeline,
    validate_missing_candles,
    validate_nulls,
    validate_ohlc,
    validate_schema,
    validate_timestamps,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UTC = timezone.utc

def make_timestamps(n: int, freq: str = "1min", start: str = "2024-01-01") -> pd.DatetimeIndex:
    """Generate n UTC-aware timestamps at the given frequency."""
    return pd.date_range(start=start, periods=n, freq=freq, tz="UTC")


def make_valid_df(n: int = 10, freq: str = "1min", start: str = "2024-01-01") -> pd.DataFrame:
    """
    Create a minimal valid canonical DataFrame for testing.
    This is a TEST FIXTURE — not real market data.
    """
    ts = make_timestamps(n, freq, start)
    ct = ts + pd.Timedelta(minutes=1) - pd.Timedelta(milliseconds=1)
    return pd.DataFrame({
        "timestamp": ts,
        "open":   pd.array([50000.0] * n, dtype="float64"),
        "high":   pd.array([50100.0] * n, dtype="float64"),
        "low":    pd.array([49900.0] * n, dtype="float64"),
        "close":  pd.array([50050.0] * n, dtype="float64"),
        "volume": pd.array([10.0] * n, dtype="float64"),
        "close_time": ct,
        "quote_volume": pd.array([500000.0] * n, dtype="float64"),
        "trade_count": pd.array([500] * n, dtype="int64"),
        "taker_buy_base_vol": pd.array([5.0] * n, dtype="float64"),
        "taker_buy_quote_vol": pd.array([250000.0] * n, dtype="float64"),
    })


# ---------------------------------------------------------------------------
# Validator 1: Schema
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_valid_df_passes(self):
        df = make_valid_df()
        result = validate_schema(df)
        assert result.status == ValidationStatus.PASS

    def test_missing_column_fails(self):
        df = make_valid_df().drop(columns=["volume"])
        result = validate_schema(df)
        assert result.status == ValidationStatus.FAIL
        assert any("volume" in issue for issue in result.issues)

    def test_multiple_missing_columns_fail(self):
        df = make_valid_df().drop(columns=["open", "close"])
        result = validate_schema(df)
        assert result.status == ValidationStatus.FAIL

    def test_naive_timestamp_fails(self):
        df = make_valid_df()
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
        result = validate_schema(df)
        assert result.status == ValidationStatus.FAIL

    def test_string_price_fails(self):
        df = make_valid_df()
        df["open"] = df["open"].astype(str)
        result = validate_schema(df)
        assert result.status == ValidationStatus.FAIL


# ---------------------------------------------------------------------------
# Validator 2: OHLC
# ---------------------------------------------------------------------------

class TestValidateOHLC:
    def test_valid_df_passes(self):
        result = validate_ohlc(make_valid_df())
        assert result.status == ValidationStatus.PASS

    def test_high_below_close_fails(self):
        df = make_valid_df()
        df.at[0, "high"] = 49000.0  # below open=50000, close=50050
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.FAIL
        assert result.stats["invalid_count"] > 0

    def test_low_above_open_fails(self):
        df = make_valid_df()
        df.at[0, "low"] = 51000.0  # above open=50000
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.FAIL

    def test_high_less_than_low_fails(self):
        df = make_valid_df()
        df.at[0, "high"] = 49000.0
        df.at[0, "low"] = 50000.0
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.FAIL

    def test_zero_price_fails(self):
        df = make_valid_df()
        df.at[0, "open"] = 0.0
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.FAIL

    def test_negative_volume_fails(self):
        df = make_valid_df()
        df.at[0, "volume"] = -1.0
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.FAIL

    def test_zero_volume_passes(self):
        """Zero volume is valid (no trades during that candle)."""
        df = make_valid_df()
        df.at[0, "volume"] = 0.0
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.PASS

    def test_doji_candle_passes(self):
        """open == high == low == close is valid (doji)."""
        df = make_valid_df()
        df["high"] = 50000.0
        df["low"] = 50000.0
        df["open"] = 50000.0
        df["close"] = 50000.0
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.PASS

    def test_empty_df_warns(self):
        df = make_valid_df(0)
        result = validate_ohlc(df)
        assert result.status == ValidationStatus.WARNING


# ---------------------------------------------------------------------------
# Validator 3: Timestamps
# ---------------------------------------------------------------------------

class TestValidateTimestamps:
    def test_valid_utc_timestamps_pass(self):
        result = validate_timestamps(make_valid_df())
        assert result.status == ValidationStatus.PASS
        assert result.stats["duplicate_count"] == 0
        assert result.stats["order_errors"] == 0

    def test_duplicate_timestamp_fails(self):
        df = make_valid_df(5)
        # Insert a duplicate
        dup = df.iloc[[2]].copy()
        df = pd.concat([df, dup], ignore_index=True)
        result = validate_timestamps(df)
        assert result.status == ValidationStatus.FAIL
        assert result.stats["duplicate_count"] > 0

    def test_non_monotonic_fails(self):
        df = make_valid_df(5)
        # Swap rows to break order
        df = df.iloc[[0, 2, 1, 3, 4]].reset_index(drop=True)
        result = validate_timestamps(df)
        assert result.status == ValidationStatus.FAIL
        assert result.stats["order_errors"] > 0

    def test_naive_timestamps_fail(self):
        df = make_valid_df(5)
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
        result = validate_timestamps(df)
        assert result.status == ValidationStatus.FAIL

    def test_non_utc_tz_fails(self):
        df = make_valid_df(5)
        df["timestamp"] = df["timestamp"].dt.tz_convert("America/Sao_Paulo")
        result = validate_timestamps(df)
        assert result.status == ValidationStatus.FAIL

    def test_empty_df_warns(self):
        result = validate_timestamps(make_valid_df(0))
        assert result.status == ValidationStatus.WARNING


# ---------------------------------------------------------------------------
# Validator 4: Missing Candles
# ---------------------------------------------------------------------------

class TestValidateMissingCandles:
    def test_complete_sequence_passes(self):
        df = make_valid_df(60, freq="1min")
        result = validate_missing_candles(df, "1m")
        assert result.status == ValidationStatus.PASS
        assert result.stats["missing_count"] == 0

    def test_gap_detected_warns(self):
        df = make_valid_df(60, freq="1min")
        # Remove 5 candles from the middle
        df = pd.concat([df.iloc[:20], df.iloc[25:]]).reset_index(drop=True)
        result = validate_missing_candles(df, "1m")
        assert result.status == ValidationStatus.WARNING
        assert result.stats["missing_count"] > 0

    def test_unknown_timeframe_warns(self):
        df = make_valid_df(10)
        result = validate_missing_candles(df, "99x")
        assert result.status == ValidationStatus.WARNING

    def test_expected_count_correct_for_1h(self):
        """1h timeframe with 24 candles over one day — expect 0 missing."""
        df = make_valid_df(24, freq="1h")
        result = validate_missing_candles(df, "1h")
        assert result.status == ValidationStatus.PASS
        assert result.stats["missing_count"] == 0

    def test_empty_df_warns(self):
        result = validate_missing_candles(make_valid_df(0), "1m")
        assert result.status == ValidationStatus.WARNING

    def test_missing_count_is_correct(self):
        """Remove exactly 3 candles and verify missing_count == 3."""
        n = 30
        df = make_valid_df(n, freq="1min")
        # Remove candles at indices 10, 11, 12
        df = pd.concat([df.iloc[:10], df.iloc[13:]]).reset_index(drop=True)
        result = validate_missing_candles(df, "1m")
        assert result.stats["missing_count"] == 3


# ---------------------------------------------------------------------------
# Validator 5: Nulls
# ---------------------------------------------------------------------------

class TestValidateNulls:
    def test_no_nulls_passes(self):
        result = validate_nulls(make_valid_df())
        assert result.status == ValidationStatus.PASS
        assert result.stats["total_null_count"] == 0

    def test_null_in_close_fails(self):
        df = make_valid_df()
        df.at[0, "close"] = float("nan")
        result = validate_nulls(df)
        assert result.status == ValidationStatus.FAIL
        assert result.stats["total_null_count"] > 0

    def test_multiple_nulls_counted(self):
        df = make_valid_df(10)
        df.at[0, "open"] = float("nan")
        df.at[1, "volume"] = float("nan")
        df.at[2, "close"] = float("nan")
        result = validate_nulls(df)
        assert result.status == ValidationStatus.FAIL
        assert result.stats["total_null_count"] == 3

    def test_empty_df_warns(self):
        result = validate_nulls(make_valid_df(0))
        assert result.status == ValidationStatus.WARNING


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestRunValidationPipeline:
    def test_clean_data_passes_all(self):
        df = make_valid_df(1440, freq="1min")
        summary = run_validation_pipeline(df, "BTCUSDT", "1m")
        assert summary.overall_status == ValidationStatus.PASS
        assert summary.row_count == 1440
        assert not summary.all_issues

    def test_corrupted_data_fails(self):
        df = make_valid_df(10)
        df.at[0, "high"] = 49000.0  # OHLC violation
        summary = run_validation_pipeline(df, "TESTUSDT", "1m")
        assert summary.overall_status == ValidationStatus.FAIL

    def test_partial_data_warns(self):
        """Data with gaps should warn, not fail (gaps are legitimate)."""
        df = make_valid_df(100, freq="1min")
        # Remove 10 candles to create a gap
        df = pd.concat([df.iloc[:40], df.iloc[50:]]).reset_index(drop=True)
        summary = run_validation_pipeline(df, "TESTUSDT", "1m")
        # Missing candles → WARNING, everything else PASS
        assert summary.overall_status == ValidationStatus.WARNING
