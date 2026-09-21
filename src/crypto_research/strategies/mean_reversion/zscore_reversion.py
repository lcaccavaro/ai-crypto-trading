"""
C3 — Z-Score Mean Reversion (ZSCORE_REV_001).

Hypothesis:
    Price moving more than a configurable number of standard deviations
    below its rolling mean (negative Z-score) may indicate a temporary
    statistical extreme. A subsequent recovery (Z-score rising above a
    higher threshold) may signal mean reversion.

Signal type: EVENT-BASED (fires when Z-score crosses above upper_threshold
after having been below lower_threshold).

Parameters:
    period:           Rolling window period (default 20).
    lower_threshold:  Z-score must fall below this to arm the signal (default -2.0).
    upper_threshold:  Z-score must cross above this to fire the signal (default -1.0).

Zero-volatility: returns None when rolling_std == 0.
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import zscore
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class ZScoreReversion(BaseStrategy):
    """
    Z-Score Mean Reversion — arms when Z-score drops below lower_threshold,
    fires LONG when Z-score recovers above upper_threshold.
    """

    _info = StrategyInfo(
        strategy_id="ZSCORE_REV_001",
        name="Z-Score Mean Reversion",
        version="1.0.0",
        category="mean_reversion",
        hypothesis=(
            "Price more than 2 standard deviations below its rolling mean may "
            "represent a statistical extreme that precedes a mean reversion. "
            "This is a research hypothesis, not a trading claim."
        ),
        description=(
            "Arms when Z-score < lower_threshold. Fires LONG when Z-score "
            "recovers above upper_threshold. Two-stage event-based signal."
        ),
        default_parameters={
            "period": 20,
            "lower_threshold": -2.0,
            "upper_threshold": -1.0,
        },
        parameter_schema={
            "period":           {"type": "int",   "default": 20,   "min": 5,    "doc": "Rolling window"},
            "lower_threshold":  {"type": "float", "default": -2.0, "max": 0.0,  "doc": "Arm level (Z-score)"},
            "upper_threshold":  {"type": "float", "default": -1.0, "max": 0.0,  "doc": "Fire level (Z-score)"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=21,
        is_event_based=True,
        notes="Returns NOT_READY (None) when std == 0.",
    )

    def __init__(
        self,
        period: int = 20,
        lower_threshold: float = -2.0,
        upper_threshold: float = -1.0,
    ) -> None:
        super().__init__()
        if period <= 0:
            raise ValueError(f"period must be > 0, got {period}")
        if lower_threshold >= upper_threshold:
            raise ValueError(
                f"lower_threshold ({lower_threshold}) must be < upper_threshold ({upper_threshold})"
            )
        self._period = period
        self._lower = lower_threshold
        self._upper = upper_threshold
        self._armed: bool = False  # True when Z-score has been below lower_threshold

    @property
    def parameters(self) -> dict:
        return {
            "period": self._period,
            "lower_threshold": self._lower,
            "upper_threshold": self._upper,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        z = zscore(closes, self._period)

        if z is None:
            return None  # zero volatility or insufficient history

        # Arm when Z-score drops below lower_threshold
        if z <= self._lower:
            self._armed = True

        # Fire when armed and Z-score recovers above upper_threshold
        if self._armed and z >= self._upper:
            self._armed = False
            return Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": f"Z-score recovered above {self._upper:.1f} after being below {self._lower:.1f}",
                    "zscore": z,
                    "period": self._period,
                },
            )

        return None

    def reset(self) -> None:
        self._armed = False
