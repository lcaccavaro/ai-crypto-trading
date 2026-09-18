"""
Data catalog — discovery and loading API for canonical OHLCV datasets.

The catalog is the primary interface between the data layer and the
backtesting engine (Prompt 03). Prompt 03 will call:

    catalog = DataCatalog()
    df = catalog.load("BTCUSDT", "1m", start=..., end=...)

without knowing anything about Binance, HTTP, Parquet files, or raw data.

The catalog also generates and maintains:

    data/metadata/dataset_manifest.json

This manifest is machine-readable and answers:
    - Which datasets exist?
    - Which symbol? Which timeframe?
    - What period is covered?
    - What is the quality status?
    - Which run created it?
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from crypto_research.core.exceptions import DataIntegrityError
from crypto_research.data.metadata import DatasetMetadata
from crypto_research.data.store import ParquetDataStore
from crypto_research.data.validators import (
    DatasetValidationSummary,
    ValidationStatus,
    run_validation_pipeline,
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DatasetInfo:
    """Lightweight descriptor for a discovered dataset."""

    symbol: str
    timeframe: str
    market_type: str
    row_count: int
    actual_start: Optional[str]
    actual_end: Optional[str]
    quality_status: str
    parquet_path: str
    metadata_path: Optional[str]
    size_bytes: int


class DataCatalog:
    """
    Programmatic data catalog for the research laboratory.

    Provides dataset discovery, loading, and validation on top of
    the ParquetDataStore. The catalog is the single entry point for
    the backtesting engine and research notebooks.

    Usage:
        catalog = DataCatalog()
        # Discover what's available
        datasets = catalog.list_datasets()
        # Load a specific dataset
        df = catalog.load("BTCUSDT", "1m", start=datetime(...), end=datetime(...))
        # Validate a stored dataset
        summary = catalog.validate_dataset("BTCUSDT", "1m")

    Point-in-time guarantee:
        catalog.load(..., end=t) returns ONLY candles before t.
        This is the fundamental non-negotiable contract for the backtester.
    """

    def __init__(
        self,
        processed_dir: Path | str = "data/processed",
        raw_dir: Path | str = "data/raw",
        metadata_dir: Path | str = "data/metadata",
        market_type: str = "futures",
    ) -> None:
        self._store = ParquetDataStore(processed_dir=processed_dir, raw_dir=raw_dir)
        self._metadata_dir = Path(metadata_dir)
        self._market_type = market_type
        self._manifest_path = self._metadata_dir / "dataset_manifest.json"

    def list_datasets(self) -> list[DatasetInfo]:
        """
        Discover all canonical datasets on disk.

        Returns:
            List of DatasetInfo objects, one per (symbol, timeframe) Parquet file.
            Returns empty list if no datasets have been downloaded yet.
        """
        raw_list = self._store.list_datasets(market_type=self._market_type)
        result = []

        for ds in raw_list:
            symbol, timeframe = ds["symbol"], ds["timeframe"]
            # Try to read metadata alongside the Parquet
            meta_path = Path(ds["path"]).parent / f"{symbol}_{timeframe}_metadata.json"
            metadata: Optional[DatasetMetadata] = None
            if meta_path.exists():
                try:
                    metadata = DatasetMetadata.load(meta_path)
                except Exception:
                    pass  # Metadata file missing/corrupt doesn't block discovery

            result.append(DatasetInfo(
                symbol=symbol,
                timeframe=timeframe,
                market_type=self._market_type,
                row_count=self._quick_row_count(ds["path"]),
                actual_start=metadata.actual_start if metadata else None,
                actual_end=metadata.actual_end if metadata else None,
                quality_status=metadata.quality_status if metadata else "UNKNOWN",
                parquet_path=ds["path"],
                metadata_path=str(meta_path) if meta_path.exists() else None,
                size_bytes=ds["size_bytes"],
            ))

        return result

    def get_dataset(self, symbol: str, timeframe: str) -> DatasetInfo:
        """
        Get info for a specific (symbol, timeframe) dataset.

        Raises:
            DataIntegrityError: If the dataset does not exist.
        """
        datasets = self.list_datasets()
        for ds in datasets:
            if ds.symbol == symbol and ds.timeframe == timeframe:
                return ds
        raise DataIntegrityError(
            f"Dataset not found in catalog: {symbol}/{timeframe} "
            f"(market_type={self._market_type}).\n"
            f"Run the ingestion pipeline to download this dataset first."
        )

    def load(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load a canonical OHLCV dataset.

        This is the primary interface for the backtesting engine (Prompt 03)
        and research notebooks.

        Point-in-time contract:
            If end is provided, candles at or after end are EXCLUDED.
            This guarantees that strategies cannot see future data.

        Args:
            symbol:    Trading pair (e.g. "BTCUSDT").
            timeframe: Candle interval (e.g. "1m").
            start:     Optional UTC-aware datetime — start filter (inclusive).
            end:       Optional UTC-aware datetime — end filter (exclusive).

        Returns:
            Canonical DataFrame, sorted ascending by timestamp.
            Empty DataFrame if no data exists.

        Raises:
            DataIntegrityError: If the dataset file is corrupt or unreadable.
        """
        df = self._store.load(
            symbol=symbol,
            timeframe=timeframe,
            market_type=self._market_type,
            start=start,
            end=end,
        )
        logger.debug(
            "Dataset loaded from catalog",
            symbol=symbol,
            timeframe=timeframe,
            rows=len(df),
            start=str(start),
            end=str(end),
        )
        return df

    def validate_dataset(self, symbol: str, timeframe: str) -> DatasetValidationSummary:
        """
        Run the full validation pipeline on a stored dataset.

        Args:
            symbol:    Trading pair.
            timeframe: Candle interval.

        Returns:
            DatasetValidationSummary with per-validator results.

        Raises:
            DataIntegrityError: If the dataset does not exist.
        """
        if not self._store.exists(symbol, timeframe, self._market_type):
            raise DataIntegrityError(
                f"Cannot validate — dataset {symbol}/{timeframe} not found on disk. "
                f"Run ingestion first."
            )
        df = self._store.load(symbol, timeframe, self._market_type)
        return run_validation_pipeline(df, symbol, timeframe)

    def is_available(self, symbol: str, timeframe: str) -> bool:
        """Return True if canonical data exists for this (symbol, timeframe)."""
        return self._store.exists(symbol, timeframe, self._market_type)

    def update_manifest(self, run_id: str) -> Path:
        """
        Rebuild and write the global dataset manifest from actual disk contents.

        The manifest is ALWAYS generated from what's actually on disk —
        never from hardcoded or fabricated content.

        Args:
            run_id: The current research run ID.

        Returns:
            Path to the written manifest JSON.
        """
        self._metadata_dir.mkdir(parents=True, exist_ok=True)

        raw_list = self._store.list_datasets(market_type=self._market_type)
        manifest_entries = []

        for ds in raw_list:
            symbol, timeframe = ds["symbol"], ds["timeframe"]
            meta_path = Path(ds["path"]).parent / f"{symbol}_{timeframe}_metadata.json"
            metadata: Optional[DatasetMetadata] = None
            if meta_path.exists():
                try:
                    metadata = DatasetMetadata.load(meta_path)
                except Exception:
                    pass

            manifest_entries.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "market_type": self._market_type,
                "parquet_path": ds["path"],
                "size_bytes": ds["size_bytes"],
                "row_count": self._quick_row_count(ds["path"]),
                "actual_start": metadata.actual_start if metadata else None,
                "actual_end": metadata.actual_end if metadata else None,
                "quality_status": metadata.quality_status if metadata else "UNKNOWN",
                "schema_version": metadata.schema_version if metadata else None,
                "data_version": metadata.data_version if metadata else None,
                "last_run_id": run_id,
                "dataset_id": metadata.dataset_id if metadata else None,
            })

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "market_type": self._market_type,
            "dataset_count": len(manifest_entries),
            "datasets": manifest_entries,
        }

        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)

        logger.info(
            "Dataset manifest updated",
            path=str(self._manifest_path),
            count=len(manifest_entries),
        )
        return self._manifest_path

    def _quick_row_count(self, parquet_path: str) -> int:
        """Read only the Parquet metadata to get row count (no full file scan)."""
        try:
            import pyarrow.parquet as pq
            pf = pq.ParquetFile(parquet_path)
            return pf.metadata.num_rows
        except Exception:
            return 0
