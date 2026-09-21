"""
B4 — Multi-Period Momentum (MULTI_MOM_001).

Hypothesis:
    When both short-term and medium-term Rate of Change are simultaneously
    above configurable thresholds, this may indicate aligned momentum across
    two time horizons, potentially increasing the probability of continuation.

Signal type: EVENT-BASED (fires when both ROC conditions are FIRST satisfied simultaneously).

Parameters:
    short_period:      Short-term ROC period (default 5).
    medium_period:     Medium-term ROC period (default 15).
    short_threshold:   Min short ROC % (default 0.5).
    medium_threshold:  Min medium ROC % (default 1.0).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import roc
from crypto_research.strategies.registry import REGISTRY


@REGISTRY.register
class MultiPeriodMomentum(BaseStrategy):
    """Multi-Period Momentum — LONG when both short and medium ROC exceed thresholds."""

    _info = StrategyInfo(
        strategy_id="MULTI_MOM_001",
        name="Multi-Period Momentum",
        version="1.0.0",
        category="momentum",
        hypothesis=(
            "Simultaneously positive ROC over short and medium horizons may indicate "
            "aligned momentum, potentially increasing continuation probability."
        ),
        description=(
            "Event-based LONG when both short_period and medium_period ROC "
            "simultaneously exceed their respective thresholds (transition event)."
        ),
        default_parameters={
            "short_period": 5,
            "medium_period": 15,
            "short_threshold": 0.5,
            "medium_threshold": 1.0,
        },
        parameter_schema={
            "short_period":     {"type": "int",   "default": 5,   "min": 1,   "doc": "Short ROC period"},
            "medium_period":    {"type": "int",   "default": 15,  "min": 2,   "doc": "Medium ROC period"},
            "short_threshold":  {"type": "float", "default": 0.5, "min": 0.0, "doc": "Min short ROC %"},
            "medium_threshold": {"type": "float", "default": 1.0, "min": 0.0, "doc": "Min medium ROC %"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=16,
        is_event_based=True,
        notes="Thresholds are not empirically optimized.",
    )

    def __init__(
        self,
        short_period: int = 5,
        medium_period: int = 15,
        short_threshold: float = 0.5,
        medium_threshold: float = 1.0,
    ) -> None:
        super().__init__()
        if short_period <= 0:
            raise ValueError(f"short_period must be > 0, got {short_period}")
        if medium_period <= short_period:
            raise ValueError(f"medium_period ({medium_period}) must be > short_period ({short_period})")
        if short_threshold < 0:
            raise ValueError(f"short_threshold must be >= 0, got {short_threshold}")
        if medium_threshold < 0:
            raise ValueError(f"medium_threshold must be >= 0, got {medium_threshold}")
        self._short = short_period
        self._medium = medium_period
        self._short_thr = short_threshold
        self._medium_thr = medium_threshold
        self._prev_both_above: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "short_period": self._short,
            "medium_period": self._medium,
            "short_threshold": self._short_thr,
            "medium_threshold": self._medium_thr,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._medium + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        short_roc = roc(closes, self._short)
        medium_roc = roc(closes, self._medium)

        if short_roc is None or medium_roc is None:
            self._prev_both_above = None
            return None

        both_above = short_roc >= self._short_thr and medium_roc >= self._medium_thr

        signal = None
        if self._prev_both_above is not None and not self._prev_both_above and both_above:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "both short and medium ROC simultaneously above thresholds",
                    "short_roc": short_roc,
                    "medium_roc": medium_roc,
                    "short_threshold": self._short_thr,
                    "medium_threshold": self._medium_thr,
                },
            )

        self._prev_both_above = both_above
        return signal

    def reset(self) -> None:
        self._prev_both_above = None
