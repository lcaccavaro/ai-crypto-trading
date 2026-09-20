"""
Backtest data provider — validates and loads canonical datasets.

Responsibilities:
    1. Validate all required datasets BEFORE the backtest starts.
    2. Load full DataFrames into memory once (columnar store is efficient).
    3. Provide HistoricalDataView — a point-in-time gated data access object
       that a strategy receives at each simulation step.

Point-In-Time Rules:
━━━━━━━━━━━━━━━━━━━

For a given simulation timestamp T:
    - A candle is AVAILABLE if its open_timestamp <= T (the candle has started).
    - A candle is CLOSED (its data is complete) only when close_time < T.

For the primary timeframe (the one generating signals):
    - Strategy receives the candle at T when that candle's close time <= T.
    - This is equivalent to: candles whose open_time < T (closed candles).

For higher timeframes (multi-timeframe analysis):
    - A 1h candle at 10:00 is ONLY available after its close_time (10:59:59).
    - At simulation time 10:15 (5m candle), the 10:00-11:00 1h candle is NOT
      available. The last available 1h candle is the 09:00-10:00 candle.
    - This prevents look-ahead from using incomplete higher-timeframe candles.

Future candle access:
    - HistoricalDataView.get() raises LookAheadBiasError if any returned
      candle has open_time > current simulation timestamp.
    - This is a hard enforcement, not a documentation note.

Signal timing:
    - Signals generated at T (from the close of candle ending at T)
      are NOT executable at T. They are marked for execution at T+1.
    - This is enforced by the engine, not the data provider.
      The data provider's job is only to expose point-in-time safe data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from crypto_research.core.domain import Timeframe
from crypto_research.core.exceptions import DataIntegrityError, LookAheadBiasError
from crypto_research.data.catalog import DataCatalog
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

# Required canonical schema columns
_REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume", "close_time"}


class BacktestDataProvider:
    """
    Validates canonical datasets and provides point-in-time gated data access.

    Usage:
        provider = BacktestDataProvider(catalog, symbols=["BTCUSDT"], timeframes=["15m"])
        provider.validate_all()  # Must call before run; raises on failure
        view = provider.get_view(current_timestamp)
        candles = view.get("BTCUSDT", "15m", n=20)  # Last 20 closed candles
    """

    def __init__(
        self,
        catalog: DataCatalog,
        symbols: list[str],
        timeframes: list[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> None:
        """
        Args:
            catalog:    DataCatalog from Prompt 02.
            symbols:    Symbols to load (e.g. ["BTCUSDT"]).
            timeframes: Timeframes to load (e.g. ["15m", "1h"]).
            start:      Optional UTC-aware start datetime (inclusive).
            end:        Optional UTC-aware end datetime (exclusive).
        """
        self._catalog = catalog
        self._symbols = symbols
        self._timeframes = timeframes
        self._start = start
        self._end = end
        # Keyed by (symbol, timeframe)
        self._data: dict[tuple[str, str], pd.DataFrame] = {}

    def validate_and_load(self) -> None:
        """
        Validate all required datasets and load them into memory.

        Validation checks (all must pass — fail loudly on any failure):
            1. Dataset exists in catalog.
            2. Dataset metadata exists.
            3. Quality status is PASS.
            4. Required schema columns are present.
            5. Timestamps are UTC-aware datetime.
            6. Data is chronologically ordered (no reversals).
            7. No duplicate timestamps.
            8. At least one row of data exists for the backtest range.

        Raises:
            DataIntegrityError: On any validation failure.
        """
        logger.info(
            "Validating backtest datasets",
            symbols=self._symbols,
            timeframes=self._timeframes,
        )

        for symbol in self._symbols:
            for timeframe in self._timeframes:
                self._validate_and_load_dataset(symbol, timeframe)

        logger.info(
            "All datasets validated and loaded",
            datasets=len(self._data),
            total_rows=sum(len(df) for df in self._data.values()),
        )

    def _validate_and_load_dataset(self, symbol: str, timeframe: str) -> None:
        """Validate and load a single (symbol, timeframe) dataset."""
        key = (symbol, timeframe)

        # 1. Check existence
        if not self._catalog.is_available(symbol, timeframe):
            raise DataIntegrityError(
                f"Dataset not found in catalog: {symbol}/{timeframe}. "
                f"Run the Prompt 02 ingestion pipeline first."
            )

        # 2. Metadata and quality check
        dataset_info = self._catalog.get_dataset(symbol, timeframe)
        if dataset_info.quality_status != "PASS":
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe} has quality_status="
                f"'{dataset_info.quality_status}'. "
                f"Only 'PASS' datasets are allowed for backtesting."
            )

        # 3. Load data
        df = self._catalog.load(symbol, timeframe, start=self._start, end=self._end)

        if df.empty:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe} is empty for the requested backtest range "
                f"[{self._start}, {self._end}). "
                f"Check that the ingested data covers this period."
            )

        # 4. Schema validation
        missing_cols = _REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe} is missing required columns: {missing_cols}"
            )

        # 5. UTC timestamp validation
        ts_col = df["timestamp"]
        if not hasattr(ts_col.dtype, "tz") or ts_col.dtype.tz is None:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe}: 'timestamp' column is not timezone-aware. "
                f"All timestamps must be UTC."
            )

        # 6. Chronological ordering
        if not ts_col.is_monotonic_increasing:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe}: timestamps are not in chronological order. "
                f"Backtesting requires strictly ordered data."
            )

        # 7. No duplicate timestamps
        n_duplicates = ts_col.duplicated().sum()
        if n_duplicates > 0:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe}: found {n_duplicates} duplicate timestamps. "
                f"Fix the ingestion pipeline before running a backtest."
            )

        self._data[key] = df.reset_index(drop=True)
        logger.info(
            "Dataset loaded",
            symbol=symbol,
            timeframe=timeframe,
            rows=len(df),
            quality=dataset_info.quality_status,
        )

    def get_view(self, current_timestamp: datetime) -> "HistoricalDataView":
        """
        Create a point-in-time data view for a given simulation timestamp.

        Args:
            current_timestamp: Current simulation timestamp (UTC-aware).

        Returns:
            HistoricalDataView exposing only data available at current_timestamp.
        """
        return HistoricalDataView(
            data=self._data,
            current_timestamp=current_timestamp,
        )

    def get_all_timestamps(self, symbol: str, timeframe: str) -> pd.Series:
        """Return all timestamps for a given (symbol, timeframe) dataset."""
        key = (symbol, timeframe)
        if key not in self._data:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe} not loaded. Call validate_and_load() first."
            )
        return self._data[key]["timestamp"]

    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Return the full loaded DataFrame for a (symbol, timeframe) pair."""
        key = (symbol, timeframe)
        if key not in self._data:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe} not loaded."
            )
        return self._data[key]

    @property
    def loaded_datasets(self) -> list[tuple[str, str]]:
        """List of (symbol, timeframe) tuples that have been loaded."""
        return list(self._data.keys())


class HistoricalDataView:
    """
    Point-in-time safe data access object passed to strategy on_candle().

    The strategy may ONLY access data through this object.
    It enforces the point-in-time rule by construction:
        - Only candles whose close_time < current_timestamp are exposed.
        - Accessing future rows raises LookAheadBiasError immediately.

    Multi-timeframe rule:
        For a 1h timeframe, at simulation time T=10:15:
            - The 09:00-10:00 1h candle is available (close_time=09:59:59 < 10:15).
            - The 10:00-11:00 1h candle is NOT available (close_time=10:59:59 > 10:15).

    Signal timing:
        This object does NOT enforce signal timing (next-candle execution).
        That is the engine's responsibility. The view simply exposes data
        that is genuinely available at the simulation timestamp.
    """

    def __init__(
        self,
        data: dict[tuple[str, str], pd.DataFrame],
        current_timestamp: datetime,
    ) -> None:
        self._data = data
        self._current_timestamp = current_timestamp
        # Normalize to UTC-aware for comparison
        if current_timestamp.tzinfo is None:
            raise DataIntegrityError(
                "HistoricalDataView current_timestamp must be UTC-aware."
            )

    @property
    def current_timestamp(self) -> datetime:
        """The simulation timestamp for this view."""
        return self._current_timestamp

    def get(
        self,
        symbol: str,
        timeframe: str,
        n: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Return closed candles available at the current simulation timestamp.

        A candle is "closed" when its close_time < current_timestamp.
        This means the candle at T is available in the view at T+1 open.

        For the primary timeframe, this means:
            At simulation step processing candle at T:
            → candles with open_time < T are available (all prior closed candles)
            → the candle at T is NOT yet available (its close_time >= T)

        For higher timeframes (e.g. 1h vs 15m):
            → 1h candle is available only after its close_time has passed

        Args:
            symbol:    Trading symbol (e.g. "BTCUSDT").
            timeframe: Candle interval (e.g. "15m").
            n:         Number of most-recent closed candles to return.
                       None = return all available closed candles.

        Returns:
            DataFrame of closed candles, sorted ascending by timestamp.
            Empty DataFrame if no closed candles exist yet.

        Raises:
            LookAheadBiasError: If the returned data contains future candles.
            DataIntegrityError: If the (symbol, timeframe) was not loaded.
        """
        key = (symbol, timeframe)
        if key not in self._data:
            raise DataIntegrityError(
                f"Dataset {symbol}/{timeframe} not loaded in BacktestDataProvider."
            )

        df = self._data[key]
        ts = self._current_timestamp

        # Filter to candles whose close_time is BEFORE the current timestamp
        # (i.e., the candle is fully closed and its data is known)
        if "close_time" in df.columns and df["close_time"].notna().any():
            mask = df["close_time"] < ts
        else:
            # Fallback: use open timestamp < current_timestamp
            mask = df["timestamp"] < ts

        available = df[mask]

        # Hard enforcement: verify no future timestamps leaked through
        if not available.empty:
            max_ts = available["timestamp"].max()
            if pd.Timestamp(max_ts) >= pd.Timestamp(ts):
                raise LookAheadBiasError(
                    f"LOOK-AHEAD BIAS DETECTED: HistoricalDataView returned candle "
                    f"at {max_ts} which is >= current simulation time {ts}. "
                    f"This is a critical engine bug. Backtesting is INVALID."
                )

        if n is not None and len(available) > n:
            available = available.tail(n)

        return available.copy()

    def get_current_price(self, symbol: str, timeframe: str) -> float | None:
        """
        Return the close price of the most recent closed candle.

        This is the last known market price at the current simulation step.

        Args:
            symbol:    Trading symbol.
            timeframe: Candle interval.

        Returns:
            Close price of last closed candle, or None if no data available.
        """
        candles = self.get(symbol, timeframe, n=1)
        if candles.empty:
            return None
        return float(candles.iloc[-1]["close"])

    def has_data(self, symbol: str, timeframe: str) -> bool:
        """Return True if any closed candles are available for (symbol, timeframe)."""
        return not self.get(symbol, timeframe, n=1).empty
