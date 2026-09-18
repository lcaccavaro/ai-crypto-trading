"""
Dataset metadata model and serialization.

Every canonical Parquet dataset is accompanied by a metadata JSON file
that records its complete provenance — who downloaded it, when, from where,
with what configuration, and what its quality status is.

This makes every dataset fully traceable back to:
    - Binance API endpoint
    - Download timestamp
    - Config snapshot (run_id → config_snapshot.yaml)
    - Processing code (git_commit)
    - Quality validation result

Design:
    DatasetMetadata is a dataclass (not Pydantic) because it must be
    created from code, not from user input. Validation is by construction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from crypto_research.core.exceptions import DataIntegrityError


@dataclass
class DatasetMetadata:
    """
    Complete provenance record for one canonical (symbol, timeframe) dataset.

    Saved as: data/processed/binance/futures/<SYMBOL>/<TF>/<SYMBOL>_<TF>_metadata.json

    Fields:
        dataset_id:        Unique identifier for this dataset (derived from symbol, tf, dates).
        symbol:            Trading pair, e.g. "BTCUSDT".
        market_type:       "futures" or "spot".
        timeframe:         Candlestick period, e.g. "1m".
        data_source:       "binance".
        source_endpoint:   Exact URL used for download.
        requested_start:   ISO string of the requested start date.
        requested_end:     ISO string of the requested end date.
        actual_start:      ISO string of the first candle's timestamp.
        actual_end:        ISO string of the last candle's timestamp.
        download_timestamp: UTC ISO string when download was completed.
        row_count:         Number of candles in the canonical dataset.
        schema_version:    Version of the canonical Parquet schema.
        data_version:      SHA-256 of the canonical Parquet file.
        quality_status:    "PASS", "WARNING", or "FAIL".
        quality_issues:    List of human-readable validation issue strings.
        missing_candles:   Count of detected missing intervals.
        duplicate_count:   Count of detected duplicate timestamps.
        invalid_ohlc_count: Count of OHLC invariant violations.
        null_count:        Count of null values.
        run_id:            Research run ID from RunManager (Prompt 01).
        git_commit:        Git commit hash at time of download (or "unavailable").
        code_version:      crypto-research package version.
    """

    # Identity
    dataset_id: str
    symbol: str
    market_type: str
    timeframe: str

    # Source
    data_source: str
    source_endpoint: str

    # Date range
    requested_start: str
    requested_end: str
    actual_start: Optional[str]
    actual_end: Optional[str]

    # Download provenance
    download_timestamp: str
    run_id: str
    git_commit: str
    code_version: str

    # Dataset stats
    row_count: int
    schema_version: str
    data_version: str  # SHA-256 of the Parquet file

    # Quality
    quality_status: str
    quality_issues: list[str] = field(default_factory=list)
    missing_candles: int = 0
    duplicate_count: int = 0
    invalid_ohlc_count: int = 0
    null_count: int = 0

    @staticmethod
    def make_dataset_id(symbol: str, timeframe: str, market_type: str) -> str:
        """Generate a deterministic dataset ID from identifying fields."""
        return f"{market_type}_{symbol}_{timeframe}".lower()

    @staticmethod
    def compute_file_checksum(path: Path) -> str:
        """
        Compute SHA-256 of a file.

        Args:
            path: Path to the file.

        Returns:
            Hex-encoded SHA-256 string.

        Raises:
            DataIntegrityError: If the file cannot be read.
        """
        if not path.exists():
            raise DataIntegrityError(
                f"Cannot compute checksum — file not found: {path}"
            )
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
        except OSError as exc:
            raise DataIntegrityError(
                f"Cannot read file for checksum computation: {path}\n{exc}"
            ) from exc
        return sha256.hexdigest()

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return asdict(self)

    def save(self, path: Path) -> None:
        """
        Write metadata to a JSON file.

        Args:
            path: Full path including filename (e.g. .../metadata.json).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load(cls, path: Path) -> "DatasetMetadata":
        """
        Load metadata from a JSON file.

        Raises:
            DataIntegrityError: If the file is missing or malformed.
        """
        if not path.exists():
            raise DataIntegrityError(
                f"Dataset metadata file not found: {path}"
            )
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise DataIntegrityError(
                f"Failed to parse dataset metadata at {path}:\n{exc}"
            ) from exc

    @classmethod
    def now_utc(cls) -> str:
        """Return the current UTC time as an ISO string."""
        return datetime.now(timezone.utc).isoformat()
