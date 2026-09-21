"""
C1 — Bollinger Band Reversion (BB_REVERSION_001).

Hypothesis:
    Price moving significantly below the lower Bollinger Band may represent
    a statistical extreme. Mean reversion hypothesis: price may revert
    toward the mean (middle band).

Signal type: EVENT-BASED (fires when price first crosses back ABOVE the lower band
from below — i.e., the reversion move, not the excursion).

Parameters:
    period:  BB period (default 20).
    num_std: Standard deviation multiplier (default 2.0).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import bollinger_bands
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class BBReversion(BaseStrategy):
    """
    BB Reversion — LONG when price crosses back above lower Bollinger Band.
    Fires on the reversion (close goes from below to above lower band).
    """

    _info = StrategyInfo(
        strategy_id="BB_REVERSION_001",
        name="Bollinger Band Reversion",
        version="1.0.0",
        category="mean_reversion",
        hypothesis=(
            "Price moving significantly below the lower Bollinger Band represents a "
            "statistical extreme. The reversion back above the lower band may signal "
            "the beginning of a mean reversion move."
        ),
        description=(
            "Event-based LONG when close crosses back above lower Bollinger Band "
            "after being below it."
        ),
        default_parameters={"period": 20, "num_std": 2.0},
        parameter_schema={
            "period":  {"type": "int",   "default": 20,  "min": 5,   "doc": "BB SMA period"},
            "num_std": {"type": "float", "default": 2.0, "min": 0.1, "doc": "Standard deviation multiplier"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=21,
        is_event_based=True,
        notes="Mean reversion is NOT assumed to be consistently profitable.",
    )

    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        super().__init__()
        if period <= 0:
            raise ValueError(f"period must be > 0, got {period}")
        if num_std <= 0:
            raise ValueError(f"num_std must be > 0, got {num_std}")
        self._period = period
        self._num_std = num_std
        self._prev_below_lower: bool | None = None

    @property
    def parameters(self) -> dict:
        return {"period": self._period, "num_std": self._num_std}

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        upper, middle, lower = bollinger_bands(closes, self._period, self._num_std)

        if lower is None:
            self._prev_below_lower = None
            return None

        below_lower = closes[-1] < lower

        signal = None
        # Reversion: was below lower, now at or above lower
        if self._prev_below_lower is not None and self._prev_below_lower and not below_lower:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "close crossed back above lower Bollinger Band",
                    "close": closes[-1],
                    "lower_band": lower,
                    "middle_band": middle,
                    "upper_band": upper,
                },
            )

        self._prev_below_lower = below_lower
        return signal

    def reset(self) -> None:
        self._prev_below_lower = None
