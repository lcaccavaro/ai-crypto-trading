"""
Parquet data store for canonical OHLCV datasets.

Canonical Parquet schema (Binance Futures):
    timestamp               datetime64[ns, UTC]   candle OPEN time
    open                    float64
    high                    float64
    low                     float64
    close                   float64
    volume                  float64               base-asset volume
    close_time              datetime64[ns, UTC]   candle CLOSE time
    quote_volume            float64
    trade_count             int64
    taker_buy_base_vol      float64
    taker_buy_quote_vol     float64

Storage layout:
    data/processed/binance/futures/<SYMBOL>/<TF>/<SYMBOL>_<TF>.parquet
    data/processed/binance/futures/<SYMBOL>/<TF>/<SYMBOL>_<TF>_metadata.json

Raw data layout:
    data/raw/binance/futures/<SYMBOL>/<TF>/raw_<UTC_ISO>.json.gz

Design notes:
    - PyArrow engine with ZSTD compression (fast decompression, good ratio).
    - Timestamp column is stored as UTC-aware datetime.
    - Schema version is recorded in Parquet metadata field 'schema_version'.
    - Files are written atomically (temp file → rename) to avoid partial writes.
    - load() supports optional start/end filtering with Pandas boolean indexing.
      (PyArrow predicate pushdown requires row groups; simple filtering is used
       here for correctness over micro-optimization.)

Timezone convention:
    ALL timestamps in canonical datasets are UTC (pytz.UTC / datetime.timezone.utc).
    Never store local machine time or exchange-local time.
    This is enforced at write time by converting to UTC before saving.
"""

from __future__ import annotations

import gzip
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from crypto_research.core.exceptions import DataIntegrityError
from crypto_research.data.binance_client import (
    KLINE_CLOSE,
    KLINE_CLOSE_TIME,
    KLINE_HIGH,
    KLINE_LOW,
    KLINE_OPEN,
    KLINE_OPEN_TIME,
    KLINE_QUOTE_VOLUME,
    KLINE_TAKER_BUY_BASE_VOL,
    KLINE_TAKER_BUY_QUOTE_VOL,
    KLINE_TRADE_COUNT,
    KLINE_VOLUME,
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

# PyArrow schema for the canonical Parquet file
# Explicit types prevent silent coercions.
CANONICAL_SCHEMA = pa.schema([
    pa.field("timestamp", pa.timestamp("ns", tz="UTC")),
    pa.field("open", pa.float64()),
    pa.field("high", pa.float64()),
    pa.field("low", pa.float64()),
    pa.field("close", pa.float64()),
    pa.field("volume", pa.float64()),
    pa.field("close_time", pa.timestamp("ns", tz="UTC")),
    pa.field("quote_volume", pa.float64()),
    pa.field("trade_count", pa.int64()),
    pa.field("taker_buy_base_vol", pa.float64()),
    pa.field("taker_buy_quote_vol", pa.float64()),
])

PARQUET_COMPRESSION = "zstd"
SCHEMA_VERSION = "1.0"


class ParquetDataStore:
    """
    Read/write canonical Parquet datasets.

    Args:
        processed_dir: Root directory for processed data
                       (default: data/processed, relative to project root).
        raw_dir:       Root directory for raw downloaded data.
    """

    def __init__(
        self,
        processed_dir: Path | str = "data/processed",
        raw_dir: Path | str = "data/raw",
    ) -> None:
        self._processed_dir = Path(processed_dir)
        self._raw_dir = Path(raw_dir)

    def _dataset_dir(self, symbol: str, timeframe: str, market_type: str) -> Path:
        """Return the directory for a specific (symbol, timeframe) canonical dataset."""
        return self._processed_dir / "binance" / market_type / symbol / timeframe

    def _parquet_path(self, symbol: str, timeframe: str, market_type: str) -> Path:
        """Return the canonical Parquet file path."""
        return self._dataset_dir(symbol, timeframe, market_type) / f"{symbol}_{timeframe}.parquet"

    def _metadata_path(self, symbol: str, timeframe: str, market_type: str) -> Path:
        """Return the metadata JSON path alongside the Parquet file."""
        return self._dataset_dir(symbol, timeframe, market_type) / f"{symbol}_{timeframe}_metadata.json"

    def _raw_dir_for(self, symbol: str, timeframe: str, market_type: str) -> Path:
        """Return the raw data directory for this (symbol, timeframe)."""
        return self._raw_dir / "binance" / market_type / symbol / timeframe

    # ------------------------------------------------------------------
    # Raw data
    # ------------------------------------------------------------------

    def save_raw(
        self,
        raw_klines: list,
        symbol: str,
        timeframe: str,
        market_type: str,
        batch_start_ms: int,
    ) -> Path:
        """
        Save raw klines JSON to disk (gzip-compressed).

        Raw data is never modified — it is the primary audit record.

        Args:
            raw_klines:     List of raw kline lists from Binance.
            symbol:         Trading pair.
            timeframe:      Candle interval.
            market_type:    "futures" or "spot".
            batch_start_ms: Start timestamp of this batch (used in filename).

        Returns:
            Path to the saved raw file.
        """
        raw_dir = self._raw_dir_for(symbol, timeframe, market_type)
        raw_dir.mkdir(parents=True, exist_ok=True)

        filename = f"raw_{batch_start_ms}.json.gz"
        path = raw_dir / filename

        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(raw_klines, f)

        logger.debug(
            "Raw data saved",
            symbol=symbol,
            timeframe=timeframe,
            path=str(path),
            rows=len(raw_klines),
        )
        return path

    # ------------------------------------------------------------------
    # Conversion: raw klines → canonical DataFrame
    # ------------------------------------------------------------------

    @staticmethod
    def raw_klines_to_dataframe(
        raw_klines: list,
        symbol: str,
        timeframe: str,
    ) -> pd.DataFrame:
        """
        Convert raw Binance klines to a canonical typed DataFrame.

        Args:
            raw_klines: List of raw kline lists from Binance.
            symbol:     Trading pair (used only for logging).
            timeframe:  Candle interval (used only for logging).

        Returns:
            Canonical DataFrame with UTC-aware timestamps and explicit dtypes.
            Returns empty DataFrame (with correct schema) if input is empty.
        """
        if not raw_klines:
            logger.debug("No raw klines to convert", symbol=symbol, timeframe=timeframe)
            return _empty_canonical_dataframe()

        records = []
        for kline in raw_klines:
            records.append({
                "timestamp":            kline[KLINE_OPEN_TIME],
                "open":                 float(kline[KLINE_OPEN]),
                "high":                 float(kline[KLINE_HIGH]),
                "low":                  float(kline[KLINE_LOW]),
                "close":                float(kline[KLINE_CLOSE]),
                "volume":               float(kline[KLINE_VOLUME]),
                "close_time":           kline[KLINE_CLOSE_TIME],
                "quote_volume":         float(kline[KLINE_QUOTE_VOLUME]),
                "trade_count":          int(kline[KLINE_TRADE_COUNT]),
                "taker_buy_base_vol":   float(kline[KLINE_TAKER_BUY_BASE_VOL]),
                "taker_buy_quote_vol":  float(kline[KLINE_TAKER_BUY_QUOTE_VOL]),
            })

        df = pd.DataFrame(records)

        # Convert millisecond timestamps to UTC-aware datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)

        # Explicit dtypes
        float_cols = ["open", "high", "low", "close", "volume",
                      "quote_volume", "taker_buy_base_vol", "taker_buy_quote_vol"]
        for col in float_cols:
            df[col] = df[col].astype("float64")
        df["trade_count"] = df["trade_count"].astype("int64")

        df = df.sort_values("timestamp").reset_index(drop=True)

        logger.debug(
            "Raw klines converted to DataFrame",
            symbol=symbol,
            timeframe=timeframe,
            rows=len(df),
        )
        return df

    # ------------------------------------------------------------------
    # Canonical Parquet write
    # ------------------------------------------------------------------

    def save(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        market_type: str,
        schema_version: str = SCHEMA_VERSION,
    ) -> Path:
        """
        Write canonical DataFrame to Parquet (atomic write).

        Atomic: writes to a temp file first, then renames. This prevents
        partial writes from corrupting the canonical dataset.

        Args:
            df:             Canonical DataFrame (must match CANONICAL_SCHEMA).
            symbol:         Trading pair.
            timeframe:      Candle interval.
            market_type:    "futures" or "spot".
            schema_version: Schema version string (recorded in Parquet metadata).

        Returns:
            Path to the saved Parquet file.

        Raises:
            DataIntegrityError: If df does not have UTC-aware timestamps.
        """
        if df.empty:
            logger.warning(
                "Skipping Parquet save — DataFrame is empty",
                symbol=symbol,
                timeframe=timeframe,
            )
            path = self._parquet_path(symbol, timeframe, market_type)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Still write an empty file so catalog can discover it
        else:
            # Enforce UTC timezone
            if hasattr(df["timestamp"].dtype, "tz"):
                tz = str(df["timestamp"].dtype.tz)
                if tz not in ("UTC", "utc"):
                    raise DataIntegrityError(
                        f"Cannot save: timestamps have timezone '{tz}', must be UTC. "
                        "All canonical data must use UTC."
                    )
            else:
                raise DataIntegrityError(
                    "Cannot save: timestamps are timezone-naive. Must be UTC-aware."
                )

        out_dir = self._dataset_dir(symbol, timeframe, market_type)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = self._parquet_path(symbol, timeframe, market_type)

        # Atomic write via temp file
        fd, tmp_path = tempfile.mkstemp(dir=out_dir, suffix=".tmp.parquet")
        os.close(fd)
        try:
            table = pa.Table.from_pandas(df, schema=CANONICAL_SCHEMA)
            # Embed schema_version in Parquet metadata
            existing_meta = table.schema.metadata or {}
            new_meta = {
                **existing_meta,
                b"schema_version": schema_version.encode(),
                b"symbol": symbol.encode(),
                b"timeframe": timeframe.encode(),
                b"market_type": market_type.encode(),
            }
            table = table.replace_schema_metadata(new_meta)
            pq.write_table(
                table,
                tmp_path,
                compression=PARQUET_COMPRESSION,
                write_statistics=True,
            )
            os.replace(tmp_path, path)  # atomic on POSIX
        except Exception as exc:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise DataIntegrityError(
                f"Failed to write Parquet for {symbol}/{timeframe}: {exc}"
            ) from exc

        logger.info(
            "Parquet saved",
            symbol=symbol,
            timeframe=timeframe,
            market_type=market_type,
            rows=len(df),
            path=str(path),
        )
        return path

    # ------------------------------------------------------------------
    # Canonical Parquet read
    # ------------------------------------------------------------------

    def load(
        self,
        symbol: str,
        timeframe: str,
        market_type: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load canonical Parquet dataset with optional time filtering.

        Point-in-time guarantee:
            If end is specified, only candles with timestamp < end are returned.
            Candles AT or AFTER end are excluded. This is the contract required
            by the backtesting engine (Prompt 03).

        Args:
            symbol:      Trading pair.
            timeframe:   Candle interval.
            market_type: "futures" or "spot".
            start:       Optional UTC-aware datetime (inclusive filter).
            end:         Optional UTC-aware datetime (exclusive filter).

        Returns:
            DataFrame ordered by timestamp. Empty DataFrame if no data exists.

        Raises:
            DataIntegrityError: If the Parquet file exists but cannot be read.
        """
        path = self._parquet_path(symbol, timeframe, market_type)
        if not path.exists():
            logger.warning(
                "Parquet file not found",
                symbol=symbol,
                timeframe=timeframe,
                path=str(path),
            )
            return _empty_canonical_dataframe()

        try:
            df = pd.read_parquet(path, engine="pyarrow")
        except Exception as exc:
            raise DataIntegrityError(
                f"Failed to read Parquet for {symbol}/{timeframe} at {path}:\n{exc}"
            ) from exc

        # Apply time filters
        if start is not None:
            if start.tzinfo is None:
                raise DataIntegrityError("start filter must be UTC-aware.")
            df = df[df["timestamp"] >= pd.Timestamp(start)]

        if end is not None:
            if end.tzinfo is None:
                raise DataIntegrityError("end filter must be UTC-aware.")
            df = df[df["timestamp"] < pd.Timestamp(end)]

        return df.reset_index(drop=True)

    def exists(self, symbol: str, timeframe: str, market_type: str) -> bool:
        """Return True if a canonical Parquet file exists for this dataset."""
        return self._parquet_path(symbol, timeframe, market_type).exists()

    def list_datasets(self, market_type: str = "futures") -> list[dict]:
        """
        Discover all canonical datasets in the processed directory.

        Returns:
            List of dicts with keys: symbol, timeframe, market_type, path, size_bytes.
        """
        base = self._processed_dir / "binance" / market_type
        datasets = []
        if not base.exists():
            return datasets

        for parquet_path in sorted(base.rglob("*.parquet")):
            parts = parquet_path.relative_to(base).parts
            # Expected structure: <SYMBOL>/<TF>/<SYMBOL>_<TF>.parquet
            if len(parts) == 3:
                symbol, timeframe = parts[0], parts[1]
                datasets.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "market_type": market_type,
                    "path": str(parquet_path),
                    "size_bytes": parquet_path.stat().st_size,
                })
        return datasets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_canonical_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame with the canonical schema."""
    return pd.DataFrame({
        "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
        "open": pd.Series(dtype="float64"),
        "high": pd.Series(dtype="float64"),
        "low": pd.Series(dtype="float64"),
        "close": pd.Series(dtype="float64"),
        "volume": pd.Series(dtype="float64"),
        "close_time": pd.Series(dtype="datetime64[ns, UTC]"),
        "quote_volume": pd.Series(dtype="float64"),
        "trade_count": pd.Series(dtype="int64"),
        "taker_buy_base_vol": pd.Series(dtype="float64"),
        "taker_buy_quote_vol": pd.Series(dtype="float64"),
    })
