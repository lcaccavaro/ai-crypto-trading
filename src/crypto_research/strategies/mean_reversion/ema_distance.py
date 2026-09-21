"""
C4 — EMA Distance Reversion (EMA_DISTANCE_001).

Hypothesis:
    When price moves a statistically significant percentage distance below
    a reference EMA, it may have extended beyond a typical reversion range.
    A recovery back toward the EMA (distance normalizing) may signal reversion.

Signal type: EVENT-BASED (fires when price recovers above the entry_distance_pct
threshold from a position where it was below exit_distance_pct).

Parameters:
    ema_period:        Reference EMA period (default 20).
    arm_distance_pct:  Price must be this % below EMA to arm (default -2.0%).
    fire_distance_pct: Price recovers to within this % of EMA to fire (default -0.5%).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import ema
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class EMADistance(BaseStrategy):
    """
    EMA Distance Reversion — arms when price drops far below EMA,
    fires LONG when price recovers toward the EMA.
    """

    _info = StrategyInfo(
        strategy_id="EMA_DISTANCE_001",
        name="EMA Distance Reversion",
        version="1.0.0",
        category="mean_reversion",
        hypothesis=(
            "When price extends significantly below a reference EMA, it may have "
            "overshot a normal range. A recovery back toward the EMA may indicate "
            "the beginning of a mean reversion."
        ),
        description=(
            "Arms when (close - EMA) / EMA * 100 <= arm_distance_pct. "
            "Fires LONG when distance recovers above fire_distance_pct."
        ),
        default_parameters={
            "ema_period": 20,
            "arm_distance_pct": -2.0,
            "fire_distance_pct": -0.5,
        },
        parameter_schema={
            "ema_period":        {"type": "int",   "default": 20,   "min": 2,    "doc": "EMA period"},
            "arm_distance_pct":  {"type": "float", "default": -2.0, "max": 0.0,  "doc": "Arm distance (% below EMA)"},
            "fire_distance_pct": {"type": "float", "default": -0.5, "max": 0.0,  "doc": "Fire distance (% below EMA)"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=21,
        is_event_based=True,
        notes="Distance thresholds are not empirically optimized.",
    )

    def __init__(
        self,
        ema_period: int = 20,
        arm_distance_pct: float = -2.0,
        fire_distance_pct: float = -0.5,
    ) -> None:
        super().__init__()
        if ema_period <= 0:
            raise ValueError(f"ema_period must be > 0, got {ema_period}")
        if arm_distance_pct >= fire_distance_pct:
            raise ValueError(
                f"arm_distance_pct ({arm_distance_pct}) must be < fire_distance_pct ({fire_distance_pct})"
            )
        if fire_distance_pct > 0:
            raise ValueError(f"fire_distance_pct must be <= 0, got {fire_distance_pct}")
        self._period = ema_period
        self._arm_pct = arm_distance_pct
        self._fire_pct = fire_distance_pct
        self._armed: bool = False

    @property
    def parameters(self) -> dict:
        return {
            "ema_period": self._period,
            "arm_distance_pct": self._arm_pct,
            "fire_distance_pct": self._fire_pct,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        ema_val = ema(closes, self._period)

        if ema_val is None or ema_val == 0.0:
            return None

        distance_pct = (closes[-1] - ema_val) / ema_val * 100.0

        # Arm when price is far below EMA
        if distance_pct <= self._arm_pct:
            self._armed = True

        # Fire when armed and price recovers
        if self._armed and distance_pct >= self._fire_pct:
            self._armed = False
            return Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": f"Price recovered to within {self._fire_pct:.1f}% of EMA",
                    "distance_pct": distance_pct,
                    "ema": ema_val,
                    "close": closes[-1],
                },
            )

        return None

    def reset(self) -> None:
        self._armed = False
