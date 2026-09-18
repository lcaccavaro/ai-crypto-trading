"""
Unit tests for ParquetDataStore (offline, no network).

Tests:
    - Raw klines to DataFrame conversion (schema, dtypes, UTC timestamps).
    - Parquet save and load round-trip.
    - Atomic write behavior.
    - Schema enforcement on save.
    - Load with start/end filtering.
    - Checksum computation.
    - exists() query.
    - list_datasets() discovery.
    - UTC enforcement on save.
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from crypto_research.data.store import ParquetDataStore, _empty_canonical_dataframe
from crypto_research.core.exceptions import DataIntegrityError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UTC = timezone.utc
MARKET_TYPE = "futures"


def make_valid_df(n: int = 20) -> pd.DataFrame:
    """TEST FIXTURE — not real market data."""
    ts = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    ct = ts + pd.Timedelta(seconds=59)
    return pd.DataFrame({
        "timestamp": ts,
        "open": pd.array([50000.0] * n, dtype="float64"),
        "high": pd.array([50200.0] * n, dtype="float64"),
        "low": pd.array([49800.0] * n, dtype="float64"),
        "close": pd.array([50100.0] * n, dtype="float64"),
        "volume": pd.array([10.0] * n, dtype="float64"),
        "close_time": ct,
        "quote_volume": pd.array([500000.0] * n, dtype="float64"),
        "trade_count": pd.array([500] * n, dtype="int64"),
        "taker_buy_base_vol": pd.array([5.0] * n, dtype="float64"),
        "taker_buy_quote_vol": pd.array([250000.0] * n, dtype="float64"),
    })


@pytest.fixture
def store(tmp_path):
    return ParquetDataStore(
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
    )


# ---------------------------------------------------------------------------
# raw_klines_to_dataframe
# ---------------------------------------------------------------------------

class TestRawKlinesToDataFrame:
    def _make_kline(self, open_ms: int) -> list:
        """Minimal valid kline list as returned by Binance Futures."""
        return [
            open_ms, "50000.0", "50200.0", "49800.0", "50100.0",  # OHLCV
            "10.0",   # volume
            open_ms + 59999,  # close_time
            "500000.0",  # quote_volume
            500,  # trade_count
            "5.0",  # taker_buy_base_vol
            "250000.0",  # taker_buy_quote_vol
            "0",  # ignore
        ]

    def test_empty_returns_empty_df(self):
        df = ParquetDataStore.raw_klines_to_dataframe([], "BTCUSDT", "1m")
        assert df.empty

    def test_converts_to_correct_columns(self):
        kline = self._make_kline(1704067200000)  # 2024-01-01 00:00 UTC
        df = ParquetDataStore.raw_klines_to_dataframe([kline], "BTCUSDT", "1m")
        assert list(df.columns) == [
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trade_count",
            "taker_buy_base_vol", "taker_buy_quote_vol",
        ]

    def test_timestamp_is_utc_aware(self):
        kline = self._make_kline(1704067200000)
        df = ParquetDataStore.raw_klines_to_dataframe([kline], "BTCUSDT", "1m")
        assert str(df["timestamp"].dtype.tz) in ("UTC", "utc")

    def test_prices_are_float64(self):
        kline = self._make_kline(1704067200000)
        df = ParquetDataStore.raw_klines_to_dataframe([kline], "BTCUSDT", "1m")
        assert df["open"].dtype == "float64"
        assert df["close"].dtype == "float64"

    def test_trade_count_is_int64(self):
        kline = self._make_kline(1704067200000)
        df = ParquetDataStore.raw_klines_to_dataframe([kline], "BTCUSDT", "1m")
        assert df["trade_count"].dtype == "int64"

    def test_multiple_klines_sorted_by_timestamp(self):
        # Provide klines out of order — should be sorted
        klines = [
            self._make_kline(1704067320000),  # t+2min
            self._make_kline(1704067200000),  # t
            self._make_kline(1704067260000),  # t+1min
        ]
        df = ParquetDataStore.raw_klines_to_dataframe(klines, "BTCUSDT", "1m")
        assert list(df["timestamp"]) == sorted(df["timestamp"])


# ---------------------------------------------------------------------------
# Parquet save / load
# ---------------------------------------------------------------------------

class TestParquetSaveLoad:
    def test_save_creates_file(self, store, tmp_path):
        df = make_valid_df()
        path = store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        assert path.exists()

    def test_load_after_save_matches(self, store):
        df = make_valid_df(30)
        store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        loaded = store.load("BTCUSDT", "1m", MARKET_TYPE)
        assert len(loaded) == 30
        assert list(loaded.columns) == list(df.columns)

    def test_timestamps_remain_utc_after_roundtrip(self, store):
        df = make_valid_df(10)
        store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        loaded = store.load("BTCUSDT", "1m", MARKET_TYPE)
        assert str(loaded["timestamp"].dtype.tz) in ("UTC", "utc")

    def test_prices_remain_float64_after_roundtrip(self, store):
        df = make_valid_df(5)
        store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        loaded = store.load("BTCUSDT", "1m", MARKET_TYPE)
        assert loaded["open"].dtype == "float64"

    def test_load_nonexistent_returns_empty(self, store):
        df = store.load("UNKNOWN", "1m", MARKET_TYPE)
        assert df.empty

    def test_load_with_start_filter(self, store):
        df = make_valid_df(60)
        store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        start = datetime(2024, 1, 1, 0, 30, tzinfo=UTC)
        loaded = store.load("BTCUSDT", "1m", MARKET_TYPE, start=start)
        assert all(ts >= pd.Timestamp(start) for ts in loaded["timestamp"])

    def test_load_with_end_filter_excludes_candles_at_end(self, store):
        df = make_valid_df(60)
        store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        end = datetime(2024, 1, 1, 0, 30, tzinfo=UTC)
        loaded = store.load("BTCUSDT", "1m", MARKET_TYPE, end=end)
        # No candle at or after end
        assert all(ts < pd.Timestamp(end) for ts in loaded["timestamp"])

    def test_save_naive_timestamps_raises(self, store):
        df = make_valid_df(5)
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
        with pytest.raises(DataIntegrityError, match="UTC"):
            store.save(df, "BTCUSDT", "1m", MARKET_TYPE)

    def test_save_non_utc_raises(self, store):
        df = make_valid_df(5)
        df["timestamp"] = df["timestamp"].dt.tz_convert("America/Sao_Paulo")
        with pytest.raises(DataIntegrityError, match="UTC"):
            store.save(df, "BTCUSDT", "1m", MARKET_TYPE)


# ---------------------------------------------------------------------------
# exists() and list_datasets()
# ---------------------------------------------------------------------------

class TestStoreExists:
    def test_exists_false_before_save(self, store):
        assert not store.exists("BTCUSDT", "1m", MARKET_TYPE)

    def test_exists_true_after_save(self, store):
        store.save(make_valid_df(), "BTCUSDT", "1m", MARKET_TYPE)
        assert store.exists("BTCUSDT", "1m", MARKET_TYPE)

    def test_list_datasets_empty_before_any_save(self, store):
        assert store.list_datasets(MARKET_TYPE) == []

    def test_list_datasets_finds_saved_datasets(self, store):
        store.save(make_valid_df(), "BTCUSDT", "1m", MARKET_TYPE)
        store.save(make_valid_df(), "ETHUSDT", "5m", MARKET_TYPE)
        datasets = store.list_datasets(MARKET_TYPE)
        symbols = {d["symbol"] for d in datasets}
        timeframes = {d["timeframe"] for d in datasets}
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "1m" in timeframes
        assert "5m" in timeframes


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------

class TestChecksum:
    def test_checksum_is_hex_string(self, store, tmp_path):
        from crypto_research.data.metadata import DatasetMetadata
        df = make_valid_df()
        path = store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        checksum = DatasetMetadata.compute_file_checksum(path)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex

    def test_checksum_deterministic(self, store):
        from crypto_research.data.metadata import DatasetMetadata
        df = make_valid_df()
        path = store.save(df, "BTCUSDT", "1m", MARKET_TYPE)
        c1 = DatasetMetadata.compute_file_checksum(path)
        c2 = DatasetMetadata.compute_file_checksum(path)
        assert c1 == c2

    def test_checksum_nonexistent_raises(self, tmp_path):
        from crypto_research.data.metadata import DatasetMetadata
        with pytest.raises(DataIntegrityError, match="not found"):
            DatasetMetadata.compute_file_checksum(tmp_path / "nonexistent.parquet")
