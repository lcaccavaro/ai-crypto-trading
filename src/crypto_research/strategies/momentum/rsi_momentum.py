"""
B1 — RSI Momentum (RSI_MOMENTUM_001).

Hypothesis:
    RSI moving above a configurable threshold from below may indicate
    emerging directional momentum, as measured by Wilder's RSI.
    Conventional thresholds (70/30) are configurable — not hardcoded.

Signal type: EVENT-BASED (fires when RSI crosses above threshold from below).

Parameters:
    rsi_period:     RSI period (default 14).
    entry_threshold: RSI level crossing triggers LONG signal (default 55).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import rsi
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class RSIMomentum(BaseStrategy):
    """RSI Momentum — LONG when RSI crosses above entry_threshold."""

    _info = StrategyInfo(
        strategy_id="RSI_MOMENTUM_001",
        name="RSI Momentum",
        version="1.0.0",
        category="momentum",
        hypothesis=(
            "RSI crossing above a configurable threshold from below may indicate "
            "emerging directional momentum. Threshold is not assumed to be optimal."
        ),
        description="Event-based LONG signal when RSI crosses above entry_threshold.",
        default_parameters={"rsi_period": 14, "entry_threshold": 55.0},
        parameter_schema={
            "rsi_period":      {"type": "int",   "default": 14,   "min": 2,  "doc": "RSI period"},
            "entry_threshold": {"type": "float", "default": 55.0, "min": 0.0, "max": 100.0,
                                "doc": "RSI level to cross for LONG signal"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=15,
        is_event_based=True,
        notes="Threshold default 55 is not claimed optimal.",
    )

    def __init__(self, rsi_period: int = 14, entry_threshold: float = 55.0) -> None:
        super().__init__()
        if rsi_period < 2:
            raise ValueError(f"rsi_period must be >= 2, got {rsi_period}")
        if not (0.0 < entry_threshold < 100.0):
            raise ValueError(f"entry_threshold must be in (0, 100), got {entry_threshold}")
        self._period = rsi_period
        self._threshold = entry_threshold
        self._prev_rsi: float | None = None

    @property
    def parameters(self) -> dict:
        return {"rsi_period": self._period, "entry_threshold": self._threshold}

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
        if (
            self._prev_rsi is not None
            and self._prev_rsi < self._threshold
            and current_rsi >= self._threshold
        ):
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=min(current_rsi / 100.0, 1.0),
                metadata={
                    "reason": f"RSI crossed above {self._threshold:.1f}",
                    "rsi": current_rsi,
                    "prev_rsi": self._prev_rsi,
                    "threshold": self._threshold,
                },
            )

        self._prev_rsi = current_rsi
        return signal

    def reset(self) -> None:
        self._prev_rsi = None
