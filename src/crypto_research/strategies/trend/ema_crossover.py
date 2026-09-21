"""
A1 — EMA Crossover Strategy (EMA_CROSS_001).

Hypothesis:
    Short-term directional momentum may be captured when a faster EMA
    crosses above a slower EMA, signaling a potential shift in trend direction.
    The crossing event (transition) is the signal — not the persistent state.

Signal type: EVENT-BASED (fires only at the crossing candle).

Parameters:
    fast_period: EMA period for the fast line (default 9).
    slow_period: EMA period for the slow line (default 21).

Stop reference: ATR-based stop is provided by the engine (not hardcoded here).

Note: These default parameters are NOT claimed to be optimal.
They exist only to make the strategy executable.
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo, Timeframe
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import ema
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class EMACrossover(BaseStrategy):
    """
    EMA Crossover — signals when fast EMA crosses above slow EMA (LONG).

    Event-based: one signal per crossover, not one per candle.
    Tracks previous crossover state to detect the crossing event.
    """

    _info = StrategyInfo(
        strategy_id="EMA_CROSS_001",
        name="EMA Crossover",
        version="1.0.0",
        category="trend",
        hypothesis=(
            "Short-term directional momentum may be captured when a faster EMA "
            "crosses above a slower EMA, signaling a potential shift in trend direction."
        ),
        description=(
            "Generates a LONG signal at the candle where fast_ema crosses above slow_ema. "
            "Event-based: fires only at the crossing event, not while fast > slow."
        ),
        default_parameters={"fast_period": 9, "slow_period": 21},
        parameter_schema={
            "fast_period": {"type": "int", "default": 9, "min": 1, "doc": "Fast EMA period"},
            "slow_period": {"type": "int", "default": 21, "min": 2, "doc": "Slow EMA period"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=22,  # slow_period + 1 for crossover detection
        is_event_based=True,
        notes="Default params are not empirically optimized.",
    )

    def __init__(self, fast_period: int = 9, slow_period: int = 21) -> None:
        super().__init__()
        if fast_period <= 0:
            raise ValueError(f"fast_period must be > 0, got {fast_period}")
        if slow_period <= 0:
            raise ValueError(f"slow_period must be > 0, got {slow_period}")
        if fast_period >= slow_period:
            raise ValueError(
                f"fast_period ({fast_period}) must be < slow_period ({slow_period})"
            )
        self._fast = fast_period
        self._slow = slow_period
        # State: was fast above slow on the previous candle? None = not yet initialized
        self._prev_fast_above: bool | None = None

    @property
    def parameters(self) -> dict:
        return {"fast_period": self._fast, "slow_period": self._slow}

    @property
    def minimum_candles_required(self) -> int:
        return self._slow + 1  # +1 for crossover detection

    def _compute_signal(
        self,
        candles: list[Candle],
        timestamp: datetime,
    ) -> Signal | None:
        closes = [c.close for c in candles]

        fast_val = ema(closes, self._fast)
        slow_val = ema(closes, self._slow)

        if fast_val is None or slow_val is None:
            self._prev_fast_above = None
            return None

        fast_above = fast_val > slow_val

        # Detect crossing: fast was below (or unknown) and is now above
        signal = None
        if self._prev_fast_above is not None and not self._prev_fast_above and fast_above:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "fast EMA crossed above slow EMA",
                    "fast_ema": fast_val,
                    "slow_ema": slow_val,
                    "fast_period": self._fast,
                    "slow_period": self._slow,
                },
            )

        self._prev_fast_above = fast_above
        return signal

    def reset(self) -> None:
        self._prev_fast_above = None
