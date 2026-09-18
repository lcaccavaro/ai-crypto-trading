"""
Data provider interface for the crypto research laboratory.

This module defines the Protocol that all data providers must implement.
Prompt 02 will implement BinanceDataProvider using this interface.

Design intent:
    - The data layer is completely decoupled from strategy and execution logic.
    - All data access must go through this interface.
    - Implementations must guarantee point-in-time correctness: data returned
      for a given (end_timestamp) must never include candles after that time.

Planned implementations (future prompts):
    - BinanceDataProvider (Prompt 02): Real historical OHLCV from Binance API.
    - FileDataProvider (Prompt 02): Reads from locally cached Parquet files.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from crypto_research.core.domain import Candle, Timeframe


@runtime_checkable
class DataProvider(Protocol):
    """
    Contract for all market data providers.

    Every implementation must satisfy this interface. This allows the
    backtester and research engine to remain completely independent of
    the concrete data source (Binance, local files, other exchanges, etc.)

    Point-in-Time guarantee:
        get_candles(asset, timeframe, start, end) must return ONLY candles
        whose open timestamp is within [start, end].
        It must NEVER return candles beyond end_timestamp.
        Violation of this guarantee introduces look-ahead bias.
    """

    @property
    def name(self) -> str:
        """Human-readable name of this data provider, e.g. 'BinanceDataProvider'."""
        ...

    @property
    def supported_assets(self) -> list[str]:
        """List of asset symbols this provider can supply data for."""
        ...

    @property
    def supported_timeframes(self) -> list[Timeframe]:
        """List of timeframes this provider can supply data for."""
        ...

    def get_candles(
        self,
        asset: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        """
        Return a list of Candle objects for the specified asset, timeframe,
        and time range [start, end] (inclusive of start, exclusive of end).

        CRITICAL REQUIREMENT — POINT-IN-TIME INTEGRITY:
            The returned candles must only contain data available at the
            simulated point in time. Candles beyond `end` must never appear.

        Args:
            asset:      Trading symbol, e.g. "BTCUSDT".
            timeframe:  Candlestick period.
            start:      UTC datetime for the start of the range (inclusive).
            end:        UTC datetime for the end of the range (exclusive).

        Returns:
            Ordered list of Candle objects (ascending by timestamp).
            Returns an empty list if no data is available for the range.

        Raises:
            DataIntegrityError: If the returned data contains integrity
                violations (e.g. out-of-order timestamps, OHLC violations).
            DataIntegrityError: If the provider returns candles beyond end.
        """
        ...

    def is_available(self, asset: str, timeframe: Timeframe) -> bool:
        """
        Check if data is available for the specified asset and timeframe.

        Args:
            asset:      Trading symbol.
            timeframe:  Candlestick period.

        Returns:
            True if data can be provided; False otherwise.
        """
        ...
