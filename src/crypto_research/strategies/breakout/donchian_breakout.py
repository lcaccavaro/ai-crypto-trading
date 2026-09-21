"""
D1 — Donchian Breakout (DONCHIAN_001).

Hypothesis:
    Price breaking above the rolling high of a prior period may indicate
    a breakout from a consolidation range, potentially signaling trend initiation.

CRITICAL PIT RULE:
    The breakout threshold is the rolling high of the PREVIOUS completed window.
    At candle T, the threshold = max(high[T-period-1 : T-1]).
    Candle T itself is NOT included in the channel calculation.

Signal type: EVENT-BASED (fires when close first breaks above prior-window high).

Parameters:
    period:      Lookback period in candles (default 20).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import donchian_channels
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class DonchianBreakout(BaseStrategy):
    """
    Donchian Breakout — LONG when close breaks above previous window's rolling high.
    Uses use_previous_window=True to ensure PIT-correct threshold.
    """

    _info = StrategyInfo(
        strategy_id="DONCHIAN_001",
        name="Donchian Channel Breakout",
        version="1.0.0",
        category="breakout",
        hypothesis=(
            "Price breaking above the rolling high of a prior period may signal "
            "a breakout from consolidation and the potential initiation of a new trend."
        ),
        description=(
            "Event-based LONG when close exceeds the prior window's rolling high. "
            "Threshold uses shift(1) window — PIT safe."
        ),
        default_parameters={"period": 20},
        parameter_schema={
            "period": {"type": "int", "default": 20, "min": 2, "doc": "Donchian channel period"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close", "high", "low"],
        warmup_period=22,
        is_event_based=True,
        notes=(
            "Uses previous completed window for threshold — candle T not included in channel. "
            "This is mandatory for PIT correctness."
        ),
    )

    def __init__(self, period: int = 20) -> None:
        super().__init__()
        if period < 2:
            raise ValueError(f"period must be >= 2, got {period}")
        self._period = period
        self._prev_above_channel: bool | None = None

    @property
    def parameters(self) -> dict:
        return {"period": self._period}

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 2  # period + current + 1 for previous window

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        # Previous window channel (PIT-safe)
        upper, lower = donchian_channels(highs, lows, self._period, use_previous_window=True)

        if upper is None:
            self._prev_above_channel = None
            return None

        above_channel = closes[-1] > upper

        signal = None
        # Fire on the crossing event (first candle above channel)
        if self._prev_above_channel is not None and not self._prev_above_channel and above_channel:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "close broke above prior-period Donchian high",
                    "close": closes[-1],
                    "donchian_upper": upper,
                    "donchian_lower": lower,
                    "period": self._period,
                },
            )

        self._prev_above_channel = above_channel
        return signal

    def reset(self) -> None:
        self._prev_above_channel = None
