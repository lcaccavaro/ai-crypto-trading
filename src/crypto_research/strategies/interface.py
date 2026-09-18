"""
Strategy interface for the crypto research laboratory.

Defines the Protocol that all strategy implementations must satisfy.
Prompt 04 will implement 15–30 strategies using this interface.

CRITICAL LOOK-AHEAD BIAS RULE:
    generate_signal() receives only historical candles up to the current
    simulation timestamp. It must NEVER:
        - access candles beyond its input slice
        - read from external data sources during backtesting
        - use any information about future candles, prices, or strategy performance
        - select parameters based on future outcomes

Strategy implementations should be deterministic:
    Given the same candles and timestamp, generate_signal() must always
    produce the same Signal (or None).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from crypto_research.core.domain import Candle, Signal, StrategyMetadata


@runtime_checkable
class Strategy(Protocol):
    """
    Contract for all strategy implementations.

    A strategy is a pure function over historical data at a point in time.
    It receives the available history and the current simulation timestamp,
    and produces a directional Signal or None (no actionable signal).

    IMPORTANT: Strategies must be stateless with respect to the simulation.
    Any state required (e.g. indicator buffers) must be derived entirely
    from the provided candle history, never from external mutable state.
    """

    @property
    def name(self) -> str:
        """Unique strategy identifier. Used for logging and reporting."""
        ...

    @property
    def version(self) -> str:
        """Strategy version string. Must be incremented when logic changes."""
        ...

    @property
    def metadata(self) -> StrategyMetadata:
        """
        Full strategy metadata including all configurable parameters.

        All parameters that can affect strategy behavior MUST appear here.
        This metadata is recorded in every research run for reproducibility.
        """
        ...

    @property
    def minimum_candles_required(self) -> int:
        """
        Minimum number of candles needed before the strategy can generate signals.

        If fewer candles are provided, generate_signal() must return None.
        This prevents look-ahead bias from warm-up periods.
        """
        ...

    def generate_signal(
        self,
        candles: list[Candle],
        timestamp: datetime,
    ) -> Signal | None:
        """
        Evaluate historical data and produce a trading signal.

        POINT-IN-TIME CONTRACT:
            - `candles` contains only candles up to and including the candle
              whose open timestamp is <= timestamp.
            - `timestamp` is the current simulation point in time.
            - The strategy must NEVER access information beyond these bounds.

        Args:
            candles:    Ordered historical candles (ascending timestamp),
                        containing only data available at `timestamp`.
                        The last candle's close is the most recently confirmed price.
            timestamp:  Current simulation timestamp. The strategy must act
                        as if it is this exact moment in time.

        Returns:
            A Signal if there is an actionable trading opportunity, or None
            if the strategy has no opinion at this time.

        Raises:
            LookAheadBiasError: If the implementation detects that it has
                accessed data beyond the provided timestamp.
            ValueError: If candles are empty or out of order.
        """
        ...
