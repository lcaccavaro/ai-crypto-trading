"""
A3 — Price vs Long-Term EMA (PRICE_VS_EMA_001).

Hypothesis:
    Price trading above a long-term EMA may indicate a bullish structural bias.
    When combined with a short-term momentum confirmation (close > prior close
    by at least a configurable minimum), this may identify high-probability
    continuation entries.

Signal type: STATE-BASED (fires whenever both conditions are met).
    The strategy generates a signal every candle where:
        1. close > EMA(long_period)
        2. short-term momentum > min_momentum_pct

To avoid consecutive identical signals, this strategy includes a
cooldown_candles parameter that suppresses re-entry signals after
a signal has fired.

Parameters:
    long_period:      Long-term EMA period (default 50).
    momentum_period:  Short-term ROC period for momentum confirmation (default 3).
    min_momentum_pct: Minimum ROC value to confirm momentum (default 0.1%).
    cooldown_candles: Minimum candles between signals (default 5, part of hypothesis).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import ema, roc
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class PriceVsEMA(BaseStrategy):
    """
    Price vs Long-Term EMA — LONG when close > long EMA and momentum confirms.
    State-based with configurable cooldown.
    """

    _info = StrategyInfo(
        strategy_id="PRICE_VS_EMA_001",
        name="Price vs Long-Term EMA",
        version="1.0.0",
        category="trend",
        hypothesis=(
            "Price trading above a long-term EMA indicates a bullish structural bias. "
            "Short-term momentum confirmation may increase signal reliability."
        ),
        description=(
            "Generates LONG signals when close > EMA(long_period) AND "
            "short-term ROC > min_momentum_pct. State-based with cooldown."
        ),
        default_parameters={
            "long_period": 50,
            "momentum_period": 3,
            "min_momentum_pct": 0.1,
            "cooldown_candles": 5,
        },
        parameter_schema={
            "long_period":      {"type": "int",   "default": 50,  "min": 5,   "doc": "Long EMA period"},
            "momentum_period":  {"type": "int",   "default": 3,   "min": 1,   "doc": "ROC lookback period"},
            "min_momentum_pct": {"type": "float", "default": 0.1, "min": 0.0, "doc": "Min ROC % for confirmation"},
            "cooldown_candles": {"type": "int",   "default": 5,   "min": 0,   "doc": "Min candles between signals"},
        },
        supported_timeframes=["15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=54,
        is_event_based=False,
        notes="Cooldown is part of the hypothesis, not artificial filtering.",
    )

    def __init__(
        self,
        long_period: int = 50,
        momentum_period: int = 3,
        min_momentum_pct: float = 0.1,
        cooldown_candles: int = 5,
    ) -> None:
        super().__init__()
        if long_period <= 0:
            raise ValueError(f"long_period must be > 0, got {long_period}")
        if momentum_period <= 0:
            raise ValueError(f"momentum_period must be > 0, got {momentum_period}")
        if min_momentum_pct < 0:
            raise ValueError(f"min_momentum_pct must be >= 0, got {min_momentum_pct}")
        if cooldown_candles < 0:
            raise ValueError(f"cooldown_candles must be >= 0, got {cooldown_candles}")
        self._long = long_period
        self._mom_period = momentum_period
        self._min_mom = min_momentum_pct
        self._cooldown = cooldown_candles
        self._candles_since_signal: int = cooldown_candles  # start ready

    @property
    def parameters(self) -> dict:
        return {
            "long_period": self._long,
            "momentum_period": self._mom_period,
            "min_momentum_pct": self._min_mom,
            "cooldown_candles": self._cooldown,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._long + self._mom_period

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]

        long_ema = ema(closes, self._long)
        roc_val = roc(closes, self._mom_period)

        if long_ema is None or roc_val is None:
            return None

        self._candles_since_signal += 1

        if (
            closes[-1] > long_ema
            and roc_val > self._min_mom
            and self._candles_since_signal >= self._cooldown
        ):
            self._candles_since_signal = 0
            return Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "close above long EMA with momentum confirmation",
                    "close": closes[-1],
                    "long_ema": long_ema,
                    "roc": roc_val,
                },
            )
        return None

    def reset(self) -> None:
        self._candles_since_signal = self._cooldown
