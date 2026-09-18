"""
BinanceDataProvider — implements the DataProvider Protocol using locally cached Parquet.

This is what the backtesting engine (Prompt 03) will use.
It reads from disk — it does NOT call the Binance API.

The separation is intentional:
    - DataIngestionPipeline: downloads data from Binance → stores Parquet
    - BinanceDataProvider:   reads from Parquet → serves Candle objects

This means backtests are fully reproducible and do not require internet access.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from crypto_research.config.schema import DataConfig, ProjectConfiguration
from crypto_research.core.domain import Candle, Timeframe
from crypto_research.core.exceptions import DataIntegrityError, LookAheadBiasError
from crypto_research.data.catalog import DataCatalog
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class BinanceDataProvider:
    """
    DataProvider implementation backed by locally cached Parquet files.

    This class satisfies the DataProvider Protocol defined in interface.py.
    It serves Candle objects to the backtesting engine without any network calls.

    Point-in-time guarantee:
        get_candles(asset, timeframe, start, end) returns ONLY candles whose
        open timestamp falls within [start, end). Candles at or after `end`
        are excluded. Violation of this contract introduces look-ahead bias.

    Usage:
        provider = BinanceDataProvider(catalog)
        candles = provider.get_candles("BTCUSDT", Timeframe.M1, start=..., end=...)
    """

    def __init__(
        self,
        catalog: DataCatalog,
        assets: Optional[list[str]] = None,
        timeframes: Optional[list[str]] = None,
    ) -> None:
        self._catalog = catalog
        self._assets = assets or []
        self._timeframes = timeframes or []

    @classmethod
    def from_config(cls, config: ProjectConfiguration) -> "BinanceDataProvider":
        """Create a BinanceDataProvider from the project configuration."""
        from pathlib import Path
        from crypto_research.config.loader import find_project_root

        root = find_project_root()
        catalog = DataCatalog(
            processed_dir=root / config.data.processed_dir,
            raw_dir=root / config.data.raw_dir,
            metadata_dir=root / config.data.metadata_dir,
            market_type=config.data.market_type,
        )
        return cls(
            catalog=catalog,
            assets=config.assets,
            timeframes=config.timeframes,
        )

    @property
    def name(self) -> str:
        return "BinanceDataProvider"

    @property
    def supported_assets(self) -> list[str]:
        return self._assets

    @property
    def supported_timeframes(self) -> list[Timeframe]:
        return [Timeframe.from_string(tf) for tf in self._timeframes]

    def get_candles(
        self,
        asset: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        """
        Return Candle objects for the specified asset, timeframe, and range.

        CRITICAL: Returns ONLY candles with open_time in [start, end).
                  Candles at or after `end` are NEVER returned.

        Args:
            asset:     Trading symbol, e.g. "BTCUSDT".
            timeframe: Candle period as Timeframe enum.
            start:     UTC-aware start datetime (inclusive).
            end:       UTC-aware end datetime (exclusive).

        Returns:
            Ordered list of Candle objects (ascending by timestamp).

        Raises:
            DataIntegrityError: If data on disk is corrupt or unreadable.
            LookAheadBiasError: If the returned data could introduce future leak
                                (defensive check — should never trigger).
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise DataIntegrityError(
                "get_candles() requires UTC-aware start and end datetimes. "
                "Naive datetimes are not permitted in research code."
            )

        if end <= start:
            raise DataIntegrityError(
                f"end ({end.isoformat()}) must be after start ({start.isoformat()})."
            )

        df = self._catalog.load(
            symbol=asset,
            timeframe=timeframe.value,
            start=start,
            end=end,
        )

        if df.empty:
            return []

        # Defensive look-ahead bias check
        max_ts = df["timestamp"].max()
        import pandas as pd
        if max_ts >= pd.Timestamp(end):
            raise LookAheadBiasError(
                f"LOOK-AHEAD BIAS DETECTED: get_candles({asset}, {timeframe.value}, "
                f"end={end.isoformat()}) returned a candle at {max_ts}. "
                f"This candle is at or after the end boundary and must not be returned. "
                f"This is a critical bug in the data layer."
            )

        candles = []
        for row in df.itertuples():
            candle = Candle(
                timestamp=row.timestamp.to_pydatetime(),
                asset=asset,
                timeframe=timeframe,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
            candles.append(candle)

        logger.debug(
            "Candles loaded",
            asset=asset,
            timeframe=timeframe.value,
            start=start.isoformat(),
            end=end.isoformat(),
            count=len(candles),
        )
        return candles

    def is_available(self, asset: str, timeframe: Timeframe) -> bool:
        """Return True if local Parquet data exists for this (asset, timeframe)."""
        return self._catalog.is_available(asset, timeframe.value)
