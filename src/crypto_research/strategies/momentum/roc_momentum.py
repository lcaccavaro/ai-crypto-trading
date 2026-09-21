"""
B2 — ROC Momentum (ROC_MOMENTUM_001).

Hypothesis:
    A price that has moved more than a configurable threshold percentage
    over a recent lookback period may exhibit momentum persistence.
    This is a pure price Rate-of-Change signal.

Signal type: EVENT-BASED (fires when ROC crosses above threshold from below).

Parameters:
    lookback:  ROC lookback period in candles (default 10).
    threshold: Minimum ROC % to trigger signal (default 1.0%).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import roc
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class ROCMomentum(BaseStrategy):
    """ROC Momentum — LONG when ROC crosses above configurable threshold."""

    _info = StrategyInfo(
        strategy_id="ROC_MOMENTUM_001",
        name="Rate of Change Momentum",
        version="1.0.0",
        category="momentum",
        hypothesis=(
            "A price that has risen more than a threshold percentage over a recent "
            "lookback may exhibit momentum persistence in the short term."
        ),
        description="Event-based LONG when ROC crosses above threshold from below.",
        default_parameters={"lookback": 10, "threshold": 1.0},
        parameter_schema={
            "lookback":  {"type": "int",   "default": 10,  "min": 1,   "doc": "ROC lookback candles"},
            "threshold": {"type": "float", "default": 1.0, "min": 0.0, "doc": "Minimum ROC % for signal"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=11,
        is_event_based=True,
        notes="Default threshold 1.0% is not empirically optimized.",
    )

    def __init__(self, lookback: int = 10, threshold: float = 1.0) -> None:
        super().__init__()
        if lookback <= 0:
            raise ValueError(f"lookback must be > 0, got {lookback}")
        if threshold < 0:
            raise ValueError(f"threshold must be >= 0, got {threshold}")
        self._lookback = lookback
        self._threshold = threshold
        self._prev_roc: float | None = None

    @property
    def parameters(self) -> dict:
        return {"lookback": self._lookback, "threshold": self._threshold}

    @property
    def minimum_candles_required(self) -> int:
        return self._lookback + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        current_roc = roc(closes, self._lookback)

        if current_roc is None:
            self._prev_roc = None
            return None

        signal = None
        if (
            self._prev_roc is not None
            and self._prev_roc < self._threshold
            and current_roc >= self._threshold
        ):
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": f"ROC crossed above threshold {self._threshold:.2f}%",
                    "roc": current_roc,
                    "threshold": self._threshold,
                    "lookback": self._lookback,
                },
            )

        self._prev_roc = current_roc
        return signal

    def reset(self) -> None:
        self._prev_roc = None
