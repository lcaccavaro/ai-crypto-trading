"""
D3 — Volatility Breakout (VOL_BREAK_001).

Hypothesis:
    A price breakout accompanied by an expansion in ATR (above its rolling
    average) may be a more reliable breakout signal than price movement alone,
    as expanding volatility may confirm the directional conviction.

Signal type: EVENT-BASED (fires when close breaks above prior high AND ATR
is above its rolling average).

Parameters:
    breakout_period: Lookback for price breakout level (default 15).
    atr_period:      ATR period (default 14).
    atr_avg_period:  Period for ATR rolling average (default 20).
    atr_multiplier:  ATR must exceed atr_multiplier * avg_atr (default 1.2).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import atr, rolling_high
from crypto_research.strategies.indicators.volatility import rolling_std
from crypto_research.strategies.registry import REGISTRY


def _atr_series_last(highs: list[float], lows: list[float], closes: list[float], period: int) -> float | None:
    """ATR for the most recent candle."""
    return atr(highs, lows, closes, period)


def _avg_atr(highs: list[float], lows: list[float], closes: list[float], atr_period: int, avg_period: int) -> float | None:
    """Compute rolling average of ATR over the last avg_period windows."""
    if len(closes) < atr_period + avg_period:
        return None
    atr_vals: list[float] = []
    for i in range(avg_period):
        idx = len(closes) - avg_period + i + 1
        h = highs[:idx]
        l_ = lows[:idx]
        c = closes[:idx]
        v = atr(h, l_, c, atr_period)
        if v is not None:
            atr_vals.append(v)
    if not atr_vals:
        return None
    return sum(atr_vals) / len(atr_vals)


@REGISTRY.register
class VolatilityBreakout(BaseStrategy):
    """
    Volatility Breakout — LONG when close breaks above prior high AND ATR is elevated.
    """

    _info = StrategyInfo(
        strategy_id="VOL_BREAK_001",
        name="Volatility Breakout",
        version="1.0.0",
        category="breakout",
        hypothesis=(
            "A price breakout accompanied by expanding ATR may be more reliable "
            "than price movement alone, as elevated volatility may confirm directional conviction."
        ),
        description=(
            "Event-based LONG when close breaks above prior rolling high AND "
            "current ATR > atr_multiplier * rolling_avg_atr."
        ),
        default_parameters={
            "breakout_period": 15,
            "atr_period": 14,
            "atr_avg_period": 20,
            "atr_multiplier": 1.2,
        },
        parameter_schema={
            "breakout_period": {"type": "int",   "default": 15,  "min": 2,   "doc": "Price breakout lookback"},
            "atr_period":      {"type": "int",   "default": 14,  "min": 2,   "doc": "ATR period"},
            "atr_avg_period":  {"type": "int",   "default": 20,  "min": 2,   "doc": "ATR average period"},
            "atr_multiplier":  {"type": "float", "default": 1.2, "min": 1.0, "doc": "ATR expansion multiplier"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["open", "high", "low", "close"],
        warmup_period=40,
        is_event_based=True,
        notes="atr_multiplier default 1.2 is not empirically optimized.",
    )

    def __init__(
        self,
        breakout_period: int = 15,
        atr_period: int = 14,
        atr_avg_period: int = 20,
        atr_multiplier: float = 1.2,
    ) -> None:
        super().__init__()
        if breakout_period < 2:
            raise ValueError(f"breakout_period must be >= 2")
        if atr_period < 2:
            raise ValueError(f"atr_period must be >= 2")
        if atr_avg_period < 2:
            raise ValueError(f"atr_avg_period must be >= 2")
        if atr_multiplier < 1.0:
            raise ValueError(f"atr_multiplier must be >= 1.0, got {atr_multiplier}")
        self._break_period = breakout_period
        self._atr_period = atr_period
        self._atr_avg_period = atr_avg_period
        self._atr_mult = atr_multiplier
        self._prev_above: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "breakout_period": self._break_period,
            "atr_period": self._atr_period,
            "atr_avg_period": self._atr_avg_period,
            "atr_multiplier": self._atr_mult,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._atr_period + self._atr_avg_period + self._break_period

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        range_top = rolling_high(highs, self._break_period, shift=1)
        current_atr = atr(highs, lows, closes, self._atr_period)
        avg_atr_val = _avg_atr(highs, lows, closes, self._atr_period, self._atr_avg_period)

        if range_top is None or current_atr is None or avg_atr_val is None:
            self._prev_above = None
            return None

        above_channel = closes[-1] > range_top
        atr_elevated = current_atr > self._atr_mult * avg_atr_val

        signal = None
        if (
            self._prev_above is not None
            and not self._prev_above
            and above_channel
            and atr_elevated
        ):
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "close broke above prior high with elevated ATR",
                    "close": closes[-1],
                    "range_top": range_top,
                    "atr": current_atr,
                    "avg_atr": avg_atr_val,
                    "atr_multiplier": self._atr_mult,
                },
            )

        self._prev_above = above_channel
        return signal

    def reset(self) -> None:
        self._prev_above = None
