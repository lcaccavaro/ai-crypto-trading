"""
C2 — RSI Extreme Reversion (RSI_EXTREME_001).

Hypothesis:
    Extreme RSI readings (below a configurable oversold threshold) may indicate
    temporary price exhaustion. A recovery from oversold — RSI crossing back
    above the threshold — may signal a mean reversion opportunity.

Signal type: EVENT-BASED (fires when RSI crosses back above oversold threshold).

Parameters:
    rsi_period:       RSI period (default 14).
    oversold_level:   RSI threshold for oversold (default 30).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import rsi
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class RSIExtreme(BaseStrategy):
    """RSI Extreme Reversion — LONG when RSI crosses back above oversold level."""

    _info = StrategyInfo(
        strategy_id="RSI_EXTREME_001",
        name="RSI Extreme Reversion",
        version="1.0.0",
        category="mean_reversion",
        hypothesis=(
            "Extreme oversold RSI readings may indicate price exhaustion. "
            "RSI recovering above the oversold level may signal the start "
            "of a mean reversion move."
        ),
        description="Event-based LONG when RSI crosses back above oversold_level.",
        default_parameters={"rsi_period": 14, "oversold_level": 30.0},
        parameter_schema={
            "rsi_period":     {"type": "int",   "default": 14,   "min": 2,    "doc": "RSI period"},
            "oversold_level": {"type": "float", "default": 30.0, "min": 0.0, "max": 50.0,
                               "doc": "RSI oversold threshold"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=15,
        is_event_based=True,
        notes="Mean reversion is NOT assumed to be consistently profitable.",
    )

    def __init__(self, rsi_period: int = 14, oversold_level: float = 30.0) -> None:
        super().__init__()
        if rsi_period < 2:
            raise ValueError(f"rsi_period must be >= 2, got {rsi_period}")
        if not (0.0 < oversold_level < 50.0):
            raise ValueError(f"oversold_level must be in (0, 50), got {oversold_level}")
        self._period = rsi_period
        self._oversold = oversold_level
        self._prev_rsi: float | None = None

    @property
    def parameters(self) -> dict:
        return {"rsi_period": self._period, "oversold_level": self._oversold}

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        current_rsi = rsi(closes, self._period)

        if current_rsi is None:
            self._prev_rsi = None
            return None

        signal = None
        # Cross back above oversold: was below, now above or equal
        if (
            self._prev_rsi is not None
            and self._prev_rsi < self._oversold
            and current_rsi >= self._oversold
        ):
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": f"RSI recovered above oversold level {self._oversold:.1f}",
                    "rsi": current_rsi,
                    "prev_rsi": self._prev_rsi,
                    "oversold_level": self._oversold,
                },
            )

        self._prev_rsi = current_rsi
        return signal

    def reset(self) -> None:
        self._prev_rsi = None
