"""
Unit tests for DatasetMetadata (offline, no network).

Tests:
    - make_dataset_id() is deterministic and lowercase.
    - to_dict() is JSON-serializable.
    - save() writes a valid JSON file.
    - load() roundtrip matches original.
    - load() on missing file raises DataIntegrityError.
    - load() on corrupt file raises DataIntegrityError.
    - now_utc() returns an ISO string.
"""

import json
from pathlib import Path

import pytest

from crypto_research.core.exceptions import DataIntegrityError
from crypto_research.data.metadata import DatasetMetadata


def make_metadata(**overrides) -> DatasetMetadata:
    """Create a test DatasetMetadata with sensible defaults."""
    defaults = dict(
        dataset_id="futures_btcusdt_1m",
        symbol="BTCUSDT",
        market_type="futures",
        timeframe="1m",
        data_source="binance",
        source_endpoint="https://fapi.binance.com/fapi/v1/klines",
        requested_start="2024-01-01T00:00:00+00:00",
        requested_end="2024-01-31T00:00:00+00:00",
        actual_start="2024-01-01T00:00:00+00:00",
        actual_end="2024-01-30T23:59:00+00:00",
        download_timestamp="2026-09-18T03:00:00+00:00",
        run_id="RUN_20260918_030000_abc123",
        git_commit="unavailable",
        code_version="1.0.0",
        row_count=43200,
        schema_version="1.0",
        data_version="abc123" * 10 + "ab12",  # 64 chars
        quality_status="PASS",
    )
    defaults.update(overrides)
    return DatasetMetadata(**defaults)


class TestDatasetMetadata:
    def test_make_dataset_id_is_lowercase(self):
        did = DatasetMetadata.make_dataset_id("BTCUSDT", "1m", "futures")
        assert did == did.lower()

    def test_make_dataset_id_deterministic(self):
        d1 = DatasetMetadata.make_dataset_id("BTCUSDT", "1m", "futures")
        d2 = DatasetMetadata.make_dataset_id("BTCUSDT", "1m", "futures")
        assert d1 == d2

    def test_make_dataset_id_differs_by_symbol(self):
        d_btc = DatasetMetadata.make_dataset_id("BTCUSDT", "1m", "futures")
        d_eth = DatasetMetadata.make_dataset_id("ETHUSDT", "1m", "futures")
        assert d_btc != d_eth

    def test_to_dict_is_json_serializable(self):
        meta = make_metadata()
        d = meta.to_dict()
        json.dumps(d)  # must not raise

    def test_to_dict_contains_required_fields(self):
        meta = make_metadata()
        d = meta.to_dict()
        required_fields = [
            "dataset_id", "symbol", "market_type", "timeframe",
            "data_source", "source_endpoint", "requested_start", "requested_end",
            "actual_start", "actual_end", "download_timestamp", "run_id",
            "git_commit", "code_version", "row_count", "schema_version",
            "data_version", "quality_status",
        ]
        for field in required_fields:
            assert field in d, f"Required field '{field}' missing"

    def test_save_creates_file(self, tmp_path):
        meta = make_metadata()
        path = tmp_path / "metadata.json"
        meta.save(path)
        assert path.exists()

    def test_save_creates_parent_dirs(self, tmp_path):
        meta = make_metadata()
        path = tmp_path / "a" / "b" / "c" / "metadata.json"
        meta.save(path)
        assert path.exists()

    def test_save_and_load_roundtrip(self, tmp_path):
        meta = make_metadata()
        path = tmp_path / "metadata.json"
        meta.save(path)
        loaded = DatasetMetadata.load(path)
        assert loaded.dataset_id == meta.dataset_id
        assert loaded.symbol == meta.symbol
        assert loaded.row_count == meta.row_count
        assert loaded.quality_status == meta.quality_status

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(DataIntegrityError, match="not found"):
            DatasetMetadata.load(tmp_path / "nonexistent.json")

    def test_load_corrupt_json_raises(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("{this is not valid json}")
        with pytest.raises(DataIntegrityError):
            DatasetMetadata.load(path)

    def test_now_utc_is_iso_string(self):
        s = DatasetMetadata.now_utc()
        assert isinstance(s, str)
        assert "T" in s  # ISO format
        assert "+" in s or "Z" in s  # UTC offset present

    def test_quality_issues_default_empty(self):
        meta = make_metadata()
        assert meta.quality_issues == []

    def test_quality_status_warning(self):
        meta = make_metadata(quality_status="WARNING", missing_candles=5)
        assert meta.quality_status == "WARNING"
        assert meta.missing_candles == 5
