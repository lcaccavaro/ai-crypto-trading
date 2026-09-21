"""
A4 — EMA Slope (EMA_SLOPE_001).

Hypothesis:
    The slope of an EMA (measured as EMA[t] > EMA[t-n]) may capture
    directional trend bias. When the EMA is rising and the close
    is above the EMA, this may indicate a healthy bullish trend.

Signal type: EVENT-BASED (fires when slope turns positive while close > EMA).

Parameters:
    ema_period:   EMA period (default 21).
    slope_period: Lookback for slope measurement (default 3).
                  Compares EMA[t] vs EMA[t - slope_period].
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import ema_series
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class EMASlope(BaseStrategy):
    """
    EMA Slope — LONG when EMA slope turns positive AND close > EMA.
    Event-based: fires only at the transition to positive slope.
    """

    _info = StrategyInfo(
        strategy_id="EMA_SLOPE_001",
        name="EMA Slope Trend",
        version="1.0.0",
        category="trend",
        hypothesis=(
            "The slope of an EMA (EMA[t] > EMA[t-n]) may capture directional trend bias. "
            "A rising EMA with price above it may indicate a healthy bullish trend."
        ),
        description=(
            "Generates LONG signal when EMA slope turns positive (EMA[t] > EMA[t-slope_period]) "
            "and close > EMA. Event-based."
        ),
        default_parameters={"ema_period": 21, "slope_period": 3},
        parameter_schema={
            "ema_period":   {"type": "int", "default": 21, "min": 2, "doc": "EMA period"},
            "slope_period": {"type": "int", "default": 3,  "min": 1, "doc": "Candles to measure slope over"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=25,
        is_event_based=True,
        notes="Default params are not empirically optimized.",
    )

    def __init__(self, ema_period: int = 21, slope_period: int = 3) -> None:
        super().__init__()
        if ema_period <= 0:
            raise ValueError(f"ema_period must be > 0, got {ema_period}")
        if slope_period <= 0:
            raise ValueError(f"slope_period must be > 0, got {slope_period}")
        self._ema_period = ema_period
        self._slope_period = slope_period
        self._prev_slope_positive: bool | None = None

    @property
    def parameters(self) -> dict:
        return {"ema_period": self._ema_period, "slope_period": self._slope_period}

    @property
    def minimum_candles_required(self) -> int:
        return self._ema_period + self._slope_period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        ema_vals = ema_series(closes, self._ema_period)

        current_ema = ema_vals[-1]
        prior_ema = ema_vals[-(self._slope_period + 1)]

        if current_ema is None or prior_ema is None:
            self._prev_slope_positive = None
            return None

        slope_positive = current_ema > prior_ema
        close_above_ema = closes[-1] > current_ema

        signal = None
        # Fire when slope TURNS positive (was not positive before)
        if (
            self._prev_slope_positive is not None
            and not self._prev_slope_positive
            and slope_positive
            and close_above_ema
        ):
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "EMA slope turned positive with close above EMA",
                    "ema_current": current_ema,
                    "ema_prior": prior_ema,
                    "close": closes[-1],
                    "slope_period": self._slope_period,
                },
            )

        self._prev_slope_positive = slope_positive
        return signal

    def reset(self) -> None:
        self._prev_slope_positive = None
