"""
A2 — Triple EMA Alignment (TRIPLE_EMA_001).

Hypothesis:
    When three EMAs of increasing periods are all aligned in bullish order
    (fast > medium > slow), this may indicate a sustained trend where momentum
    and trend direction are consistent across multiple time horizons.

Signal type: EVENT-BASED (fires at the candle when alignment first becomes true).

Parameters:
    fast_period:   Fastest EMA (default 5).
    medium_period: Middle EMA (default 13).
    slow_period:   Slowest EMA (default 34).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import ema
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class TripleEMA(BaseStrategy):
    """
    Triple EMA Alignment — fires LONG when fast > medium > slow (on transition).
    """

    _info = StrategyInfo(
        strategy_id="TRIPLE_EMA_001",
        name="Triple EMA Alignment",
        version="1.0.0",
        category="trend",
        hypothesis=(
            "When three EMAs of increasing periods align bullishly (fast > medium > slow), "
            "momentum and trend direction may be consistent across multiple time horizons."
        ),
        description=(
            "Generates a LONG signal at the candle where all three EMAs first enter "
            "bullish alignment. Event-based."
        ),
        default_parameters={"fast_period": 5, "medium_period": 13, "slow_period": 34},
        parameter_schema={
            "fast_period":   {"type": "int", "default": 5,  "min": 1, "doc": "Fast EMA period"},
            "medium_period": {"type": "int", "default": 13, "min": 2, "doc": "Medium EMA period"},
            "slow_period":   {"type": "int", "default": 34, "min": 3, "doc": "Slow EMA period"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=35,
        is_event_based=True,
        notes="Default params are not empirically optimized.",
    )

    def __init__(
        self,
        fast_period: int = 5,
        medium_period: int = 13,
        slow_period: int = 34,
    ) -> None:
        super().__init__()
        if fast_period <= 0:
            raise ValueError(f"fast_period must be > 0, got {fast_period}")
        if medium_period <= fast_period:
            raise ValueError(f"medium_period ({medium_period}) must be > fast_period ({fast_period})")
        if slow_period <= medium_period:
            raise ValueError(f"slow_period ({slow_period}) must be > medium_period ({medium_period})")
        self._fast = fast_period
        self._medium = medium_period
        self._slow = slow_period
        self._prev_aligned: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "fast_period": self._fast,
            "medium_period": self._medium,
            "slow_period": self._slow,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._slow + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        fast_val = ema(closes, self._fast)
        medium_val = ema(closes, self._medium)
        slow_val = ema(closes, self._slow)

        if fast_val is None or medium_val is None or slow_val is None:
            self._prev_aligned = None
            return None

        aligned = fast_val > medium_val > slow_val

        signal = None
        if self._prev_aligned is not None and not self._prev_aligned and aligned:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "triple EMA aligned bullish (fast > medium > slow)",
                    "fast_ema": fast_val,
                    "medium_ema": medium_val,
                    "slow_ema": slow_val,
                },
            )

        self._prev_aligned = aligned
        return signal

    def reset(self) -> None:
        self._prev_aligned = None
