"""
B3 — MACD Momentum (MACD_MOMENTUM_001).

Hypothesis:
    A MACD histogram crossing from negative to positive may indicate
    that short-term momentum is turning bullish. The MACD crossover
    (MACD line crossing above signal line) is used as the signal event.

Signal type: EVENT-BASED (fires when MACD line crosses above signal line).

Parameters:
    fast_period:   Fast EMA period (default 12).
    slow_period:   Slow EMA period (default 26).
    signal_period: Signal line EMA period (default 9).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import macd
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class MACDMomentum(BaseStrategy):
    """MACD Momentum — LONG when MACD line crosses above signal line."""

    _info = StrategyInfo(
        strategy_id="MACD_MOMENTUM_001",
        name="MACD Momentum",
        version="1.0.0",
        category="momentum",
        hypothesis=(
            "A MACD histogram crossing from negative to positive indicates that "
            "short-term momentum is turning bullish. The event may predict short-term "
            "directional continuation."
        ),
        description="Event-based LONG when MACD line crosses above signal line (histogram goes positive).",
        default_parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        parameter_schema={
            "fast_period":   {"type": "int", "default": 12, "min": 1, "doc": "Fast EMA period"},
            "slow_period":   {"type": "int", "default": 26, "min": 2, "doc": "Slow EMA period"},
            "signal_period": {"type": "int", "default": 9,  "min": 1, "doc": "Signal line period"},
        },
        supported_timeframes=["15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=35,
        is_event_based=True,
        notes="Default MACD params 12/26/9 are standard but not empirically optimized here.",
    )

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> None:
        super().__init__()
        if fast_period <= 0:
            raise ValueError(f"fast_period must be > 0, got {fast_period}")
        if slow_period <= 0:
            raise ValueError(f"slow_period must be > 0, got {slow_period}")
        if fast_period >= slow_period:
            raise ValueError(f"fast_period ({fast_period}) must be < slow_period ({slow_period})")
        if signal_period <= 0:
            raise ValueError(f"signal_period must be > 0, got {signal_period}")
        self._fast = fast_period
        self._slow = slow_period
        self._signal = signal_period
        self._prev_histogram: float | None = None

    @property
    def parameters(self) -> dict:
        return {
            "fast_period": self._fast,
            "slow_period": self._slow,
            "signal_period": self._signal,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._slow + self._signal

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        macd_line, signal_line, histogram = macd(closes, self._fast, self._slow, self._signal)

        if histogram is None:
            self._prev_histogram = None
            return None

        signal = None
        # Crossing from negative to positive
        if self._prev_histogram is not None and self._prev_histogram < 0 and histogram >= 0:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "MACD histogram crossed from negative to positive",
                    "macd_line": macd_line,
                    "signal_line": signal_line,
                    "histogram": histogram,
                    "prev_histogram": self._prev_histogram,
                },
            )

        self._prev_histogram = histogram
        return signal

    def reset(self) -> None:
        self._prev_histogram = None
