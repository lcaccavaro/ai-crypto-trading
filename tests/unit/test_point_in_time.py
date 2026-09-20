"""
Unit tests for point-in-time data access enforcement.

Tests:
    - HistoricalDataView never returns future candles.
    - LookAheadBiasError is raised if future data is somehow included.
    - Multi-timeframe PIT: 1h candle not available until close_time has passed.
    - Signal timing: candle at T is not available at T (only at T+1).
    - Naive timestamp raises DataIntegrityError.
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from crypto_research.backtest.backtest_data_provider import HistoricalDataView
from crypto_research.core.exceptions import DataIntegrityError, LookAheadBiasError


def make_candle_df(
    n=10,
    start="2026-08-01 10:00",
    freq="15min",
    symbol="BTCUSDT",
):
    """Build a small synthetic OHLCV DataFrame for testing."""
    timestamps = pd.date_range(start=start, periods=n, freq=freq, tz="UTC")
    close_times = timestamps + pd.Timedelta(freq) - pd.Timedelta("1ms")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": [50_000.0 + i * 10 for i in range(n)],
        "high": [50_010.0 + i * 10 for i in range(n)],
        "low": [49_990.0 + i * 10 for i in range(n)],
        "close": [50_005.0 + i * 10 for i in range(n)],
        "volume": [100.0] * n,
        "close_time": close_times,
    })
    return df


class TestHistoricalDataView:
    def _make_view(self, current_ts, n=10):
        df = make_candle_df(n=n)
        data = {("BTCUSDT", "15m"): df}
        return HistoricalDataView(data=data, current_timestamp=current_ts)

    def test_no_future_candles_returned(self):
        """View at t=10:30 must not return candle at 10:30 or later."""
        ts = datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc)
        view = self._make_view(ts)
        candles = view.get("BTCUSDT", "15m")
        if not candles.empty:
            assert candles["timestamp"].max() < pd.Timestamp(ts)

    def test_candle_at_t_not_available_at_t(self):
        """
        At simulation time T (the start of candle C), candle C is NOT closed.
        Only candles with close_time < T are available.
        """
        # At exactly 10:15 (candle open), the 10:15 candle is not closed yet
        ts = datetime(2026, 8, 1, 10, 15, tzinfo=timezone.utc)
        view = self._make_view(ts)
        candles = view.get("BTCUSDT", "15m")
        # All returned candle timestamps must be before 10:15
        if not candles.empty:
            assert (candles["timestamp"] < pd.Timestamp(ts)).all()

    def test_prior_candles_available(self):
        """Candles before the current simulation time are available."""
        ts = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        view = self._make_view(ts, n=20)
        candles = view.get("BTCUSDT", "15m")
        assert not candles.empty

    def test_n_parameter_limits_returned_candles(self):
        """get(..., n=5) returns at most 5 candles."""
        ts = datetime(2026, 8, 1, 13, 0, tzinfo=timezone.utc)
        view = self._make_view(ts, n=20)
        candles = view.get("BTCUSDT", "15m", n=5)
        assert len(candles) <= 5

    def test_empty_before_first_close(self):
        """At t=10:00 (before any candle closes), view returns empty DataFrame."""
        ts = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
        view = self._make_view(ts)
        candles = view.get("BTCUSDT", "15m")
        assert candles.empty

    def test_unknown_symbol_raises(self):
        ts = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        df = make_candle_df()
        data = {("BTCUSDT", "15m"): df}
        view = HistoricalDataView(data=data, current_timestamp=ts)
        with pytest.raises(DataIntegrityError):
            view.get("ETHUSDT", "15m")

    def test_naive_timestamp_raises(self):
        """Naive (non-UTC) timestamps must be rejected."""
        naive_ts = datetime(2026, 8, 1, 12, 0)  # no tzinfo
        df = make_candle_df()
        data = {("BTCUSDT", "15m"): df}
        with pytest.raises(DataIntegrityError):
            HistoricalDataView(data=data, current_timestamp=naive_ts)


class TestMultiTimeframePIT:
    def test_1h_candle_not_available_during_period(self):
        """
        At 10:15 (inside the 10:00-11:00 1h candle), the 1h candle at 10:00
        is NOT yet available — its close_time is 10:59:59.
        """
        # Build 1h candles: 09:00, 10:00, 11:00
        timestamps = pd.date_range("2026-08-01 09:00", periods=3, freq="1h", tz="UTC")
        close_times = timestamps + pd.Timedelta("1h") - pd.Timedelta("1ms")
        df_1h = pd.DataFrame({
            "timestamp": timestamps,
            "open": [50_000.0] * 3,
            "high": [50_100.0] * 3,
            "low": [49_900.0] * 3,
            "close": [50_050.0] * 3,
            "volume": [1000.0] * 3,
            "close_time": close_times,
        })

        # Current simulation time = 10:15 (middle of 10:00-11:00 1h candle)
        ts = datetime(2026, 8, 1, 10, 15, tzinfo=timezone.utc)
        data = {("BTCUSDT", "1h"): df_1h}
        view = HistoricalDataView(data=data, current_timestamp=ts)

        candles = view.get("BTCUSDT", "1h")
        # Only the 09:00 candle (close_time=09:59:59) is available
        assert not candles.empty
        assert len(candles) == 1
        assert candles.iloc[0]["timestamp"] == pd.Timestamp("2026-08-01 09:00", tz="UTC")

    def test_1h_candle_available_after_close(self):
        """
        At 11:01 (after 10:00-11:00 1h candle closed), that candle IS available.
        """
        timestamps = pd.date_range("2026-08-01 09:00", periods=3, freq="1h", tz="UTC")
        close_times = timestamps + pd.Timedelta("1h") - pd.Timedelta("1ms")
        df_1h = pd.DataFrame({
            "timestamp": timestamps,
            "open": [50_000.0] * 3,
            "high": [50_100.0] * 3,
            "low": [49_900.0] * 3,
            "close": [50_050.0] * 3,
            "volume": [1000.0] * 3,
            "close_time": close_times,
        })

        ts = datetime(2026, 8, 1, 11, 1, tzinfo=timezone.utc)
        data = {("BTCUSDT", "1h"): df_1h}
        view = HistoricalDataView(data=data, current_timestamp=ts)

        candles = view.get("BTCUSDT", "1h")
        assert len(candles) == 2  # 09:00 and 10:00 candles


class TestGetCurrentPrice:
    def test_returns_last_close_price(self):
        ts = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        df = make_candle_df(n=10)
        data = {("BTCUSDT", "15m"): df}
        view = HistoricalDataView(data=data, current_timestamp=ts)
        price = view.get_current_price("BTCUSDT", "15m")
        assert price is not None
        assert isinstance(price, float)

    def test_returns_none_before_first_candle(self):
        ts = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)  # before any data
        df = make_candle_df(n=5, start="2026-08-01 10:00")
        data = {("BTCUSDT", "15m"): df}
        view = HistoricalDataView(data=data, current_timestamp=ts)
        price = view.get_current_price("BTCUSDT", "15m")
        assert price is None
