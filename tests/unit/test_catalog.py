"""
Unit tests for DataCatalog (offline, no network).

Tests:
    - list_datasets() on empty directory.
    - list_datasets() discovers multiple datasets.
    - get_dataset() raises DataIntegrityError if not found.
    - load() returns correct DataFrame.
    - load() with start/end filtering works.
    - is_available() returns correct bool.
    - validate_dataset() raises DataIntegrityError if not found.
    - validate_dataset() returns correct summary for valid data.
    - update_manifest() creates a JSON file from actual disk contents.
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from crypto_research.core.exceptions import DataIntegrityError
from crypto_research.data.catalog import DataCatalog
from crypto_research.data.store import ParquetDataStore
from crypto_research.data.validators import ValidationStatus

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
def catalog(tmp_path) -> DataCatalog:
    return DataCatalog(
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
        metadata_dir=tmp_path / "metadata",
        market_type=MARKET_TYPE,
    )


@pytest.fixture
def store(tmp_path) -> ParquetDataStore:
    return ParquetDataStore(
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
    )


@pytest.fixture
def catalog_with_data(tmp_path) -> DataCatalog:
    """Catalog pre-populated with BTCUSDT/1m and ETHUSDT/5m datasets."""
    store = ParquetDataStore(
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
    )
    store.save(make_valid_df(60), "BTCUSDT", "1m", MARKET_TYPE)
    store.save(make_valid_df(60), "ETHUSDT", "5m", MARKET_TYPE)
    return DataCatalog(
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
        metadata_dir=tmp_path / "metadata",
        market_type=MARKET_TYPE,
    )


class TestListDatasets:
    def test_empty_catalog(self, catalog):
        assert catalog.list_datasets() == []

    def test_discovers_saved_datasets(self, catalog_with_data):
        datasets = catalog_with_data.list_datasets()
        assert len(datasets) == 2
        symbols = {d.symbol for d in datasets}
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols

    def test_dataset_info_has_correct_timeframe(self, catalog_with_data):
        datasets = catalog_with_data.list_datasets()
        tf_map = {d.symbol: d.timeframe for d in datasets}
        assert tf_map["BTCUSDT"] == "1m"
        assert tf_map["ETHUSDT"] == "5m"

    def test_market_type_is_correct(self, catalog_with_data):
        datasets = catalog_with_data.list_datasets()
        for d in datasets:
            assert d.market_type == MARKET_TYPE


class TestGetDataset:
    def test_get_existing_dataset(self, catalog_with_data):
        ds = catalog_with_data.get_dataset("BTCUSDT", "1m")
        assert ds.symbol == "BTCUSDT"
        assert ds.timeframe == "1m"

    def test_get_nonexistent_raises(self, catalog):
        with pytest.raises(DataIntegrityError, match="not found"):
            catalog.get_dataset("SOLUSDT", "1m")


class TestLoad:
    def test_load_returns_correct_rows(self, catalog_with_data):
        df = catalog_with_data.load("BTCUSDT", "1m")
        assert len(df) == 60

    def test_load_empty_if_not_found(self, catalog):
        df = catalog.load("UNKNOWN", "1m")
        assert df.empty

    def test_load_with_start_filter(self, catalog_with_data):
        start = datetime(2024, 1, 1, 0, 30, tzinfo=UTC)
        df = catalog_with_data.load("BTCUSDT", "1m", start=start)
        if not df.empty:
            assert all(ts >= pd.Timestamp(start) for ts in df["timestamp"])

    def test_load_with_end_excludes_candles_at_end(self, catalog_with_data):
        end = datetime(2024, 1, 1, 0, 30, tzinfo=UTC)
        df = catalog_with_data.load("BTCUSDT", "1m", end=end)
        if not df.empty:
            assert all(ts < pd.Timestamp(end) for ts in df["timestamp"])

    def test_load_timestamps_are_utc(self, catalog_with_data):
        df = catalog_with_data.load("BTCUSDT", "1m")
        assert str(df["timestamp"].dtype.tz) in ("UTC", "utc")


class TestIsAvailable:
    def test_not_available_before_download(self, catalog):
        assert not catalog.is_available("BTCUSDT", "1m")

    def test_available_after_save(self, catalog_with_data):
        assert catalog_with_data.is_available("BTCUSDT", "1m")
        assert catalog_with_data.is_available("ETHUSDT", "5m")


class TestValidateDataset:
    def test_validate_nonexistent_raises(self, catalog):
        with pytest.raises(DataIntegrityError, match="not found"):
            catalog.validate_dataset("BTCUSDT", "1m")

    def test_validate_clean_data_passes(self, catalog_with_data):
        summary = catalog_with_data.validate_dataset("BTCUSDT", "1m")
        # Missing candles expected due to only 60 rows; overall may be WARNING
        assert summary.overall_status in (ValidationStatus.PASS, ValidationStatus.WARNING)
        assert summary.row_count == 60


class TestUpdateManifest:
    def test_manifest_created(self, catalog_with_data, tmp_path):
        path = catalog_with_data.update_manifest("RUN_TEST_001")
        assert path.exists()

    def test_manifest_is_valid_json(self, catalog_with_data, tmp_path):
        import json
        path = catalog_with_data.update_manifest("RUN_TEST_001")
        with open(path) as f:
            manifest = json.load(f)
        assert isinstance(manifest, dict)
        assert "datasets" in manifest

    def test_manifest_count_matches_datasets(self, catalog_with_data):
        import json
        path = catalog_with_data.update_manifest("RUN_TEST_001")
        with open(path) as f:
            manifest = json.load(f)
        assert manifest["dataset_count"] == 2

    def test_manifest_from_actual_disk_not_hardcoded(self, catalog_with_data):
        """Manifest must reflect what's actually on disk."""
        import json
        path = catalog_with_data.update_manifest("RUN_TEST_001")
        with open(path) as f:
            manifest = json.load(f)
        symbols = {d["symbol"] for d in manifest["datasets"]}
        assert symbols == {"BTCUSDT", "ETHUSDT"}
