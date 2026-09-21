"""
D4 — ATR Channel Breakout (ATR_CHANNEL_001).

Hypothesis:
    An ATR-based channel (reference EMA ± atr_multiplier * ATR) defines
    a dynamic price envelope. When price closes above the upper channel,
    it may signal a directional breakout beyond normal volatility range.

Note on D4 design choice:
    Prompt 04 specifies D4 as "Opening/Session Range Breakout" but notes:
    "Only implement if the project's market/session model supports it correctly."
    Binance operates 24/7 with no native session boundaries. Arbitrary session
    boundaries would be undocumented assumptions.
    Therefore D4 is replaced with ATR Channel Breakout — a well-defined
    hypothesis that does not require session semantics.

Signal type: EVENT-BASED (fires when close crosses above upper ATR channel).

Parameters:
    ema_period:      Reference EMA period (default 20).
    atr_period:      ATR period (default 14).
    atr_multiplier:  Channel width multiplier (default 1.5).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import atr, ema
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class ATRChannelBreakout(BaseStrategy):
    """
    ATR Channel Breakout — LONG when close crosses above EMA + atr_multiplier * ATR.
    """

    _info = StrategyInfo(
        strategy_id="ATR_CHANNEL_001",
        name="ATR Channel Breakout",
        version="1.0.0",
        category="breakout",
        hypothesis=(
            "An ATR-based channel defines a dynamic price envelope around a reference EMA. "
            "A close above the upper channel may signal a breakout beyond normal volatility range."
        ),
        description=(
            "Event-based LONG when close crosses above (EMA + atr_multiplier * ATR). "
            "Replaces session-range breakout (not applicable to 24/7 Binance markets)."
        ),
        default_parameters={"ema_period": 20, "atr_period": 14, "atr_multiplier": 1.5},
        parameter_schema={
            "ema_period":     {"type": "int",   "default": 20,  "min": 2,   "doc": "Reference EMA period"},
            "atr_period":     {"type": "int",   "default": 14,  "min": 2,   "doc": "ATR period"},
            "atr_multiplier": {"type": "float", "default": 1.5, "min": 0.1, "doc": "ATR channel width multiplier"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["high", "low", "close"],
        warmup_period=22,
        is_event_based=True,
        notes=(
            "Replaces session range breakout — Binance 24/7 has no natural session. "
            "atr_multiplier default 1.5 is not empirically optimized."
        ),
    )

    def __init__(
        self,
        ema_period: int = 20,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
    ) -> None:
        super().__init__()
        if ema_period <= 0:
            raise ValueError(f"ema_period must be > 0, got {ema_period}")
        if atr_period <= 0:
            raise ValueError(f"atr_period must be > 0, got {atr_period}")
        if atr_multiplier <= 0:
            raise ValueError(f"atr_multiplier must be > 0, got {atr_multiplier}")
        self._ema_period = ema_period
        self._atr_period = atr_period
        self._atr_mult = atr_multiplier
        self._prev_above: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "ema_period": self._ema_period,
            "atr_period": self._atr_period,
            "atr_multiplier": self._atr_mult,
        }

    @property
    def minimum_candles_required(self) -> int:
        return max(self._ema_period, self._atr_period) + 2

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        ema_val = ema(closes, self._ema_period)
        atr_val = atr(highs, lows, closes, self._atr_period)

        if ema_val is None or atr_val is None:
            self._prev_above = None
            return None

        upper_channel = ema_val + self._atr_mult * atr_val
        above = closes[-1] > upper_channel

        signal = None
        if self._prev_above is not None and not self._prev_above and above:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "close crossed above ATR upper channel",
                    "close": closes[-1],
                    "ema": ema_val,
                    "atr": atr_val,
                    "upper_channel": upper_channel,
                    "atr_multiplier": self._atr_mult,
                },
            )

        self._prev_above = above
        return signal

    def reset(self) -> None:
        self._prev_above = None
