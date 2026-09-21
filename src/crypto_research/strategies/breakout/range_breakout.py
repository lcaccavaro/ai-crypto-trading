"""
D2 — Range Breakout (RANGE_BREAK_001).

Hypothesis:
    When price consolidates within a narrow rolling range (high - low)
    relative to price, a breakout above the top of that range may signal
    the start of a directional move.

Signal type: EVENT-BASED (fires when close exceeds prior range high).

Parameters:
    period: Rolling range lookback period (default 15).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import rolling_high
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class RangeBreakout(BaseStrategy):
    """
    Range Breakout — LONG when close breaks above prior period's rolling high.
    Uses shift=1 to ensure PIT-correct comparison.
    """

    _info = StrategyInfo(
        strategy_id="RANGE_BREAK_001",
        name="Range Breakout",
        version="1.0.0",
        category="breakout",
        hypothesis=(
            "Price consolidating in a rolling range followed by a close above the "
            "top of that range may signal a directional breakout."
        ),
        description="Event-based LONG when close exceeds prior period high (shift=1).",
        default_parameters={"period": 15},
        parameter_schema={
            "period": {"type": "int", "default": 15, "min": 2, "doc": "Rolling range period"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close", "high"],
        warmup_period=17,
        is_event_based=True,
        notes="Range high uses shift=1 (prior completed window) for PIT correctness.",
    )

    def __init__(self, period: int = 15) -> None:
        super().__init__()
        if period < 2:
            raise ValueError(f"period must be >= 2, got {period}")
        self._period = period
        self._prev_above: bool | None = None

    @property
    def parameters(self) -> dict:
        return {"period": self._period}

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 2

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        closes = [c.close for c in candles]

        # Prior window rolling high (shift=1 = exclude current candle)
        range_top = rolling_high(highs, self._period, shift=1)

        if range_top is None:
            self._prev_above = None
            return None

        above = closes[-1] > range_top

        signal = None
        if self._prev_above is not None and not self._prev_above and above:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "close broke above prior-period rolling high",
                    "close": closes[-1],
                    "range_top": range_top,
                    "period": self._period,
                },
            )

        self._prev_above = above
        return signal

    def reset(self) -> None:
        self._prev_above = None
