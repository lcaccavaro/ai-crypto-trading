"""
Group F — Volume strategies.

F1 — Volume Spike Confirmation (VOL_SPIKE_001).
F2 — Volume-Weighted Momentum (VOL_WGT_MOM_001).
F3 — Volume Breakout Confirmation (VOL_BREAK_CONF_001).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import relative_volume, roc, rolling_high
from crypto_research.strategies.registry import REGISTRY


# ---------------------------------------------------------------------------
# F1 — Volume Spike Confirmation
# ---------------------------------------------------------------------------

@REGISTRY.register
class VolumeSpike(BaseStrategy):
    """
    F1 — Volume Spike: LONG when there is an unusually high volume spike
    combined with positive price action (close > open on the current candle).
    """

    _info = StrategyInfo(
        strategy_id="VOL_SPIKE_001",
        name="Volume Spike Confirmation",
        version="1.0.0",
        category="volume",
        hypothesis=(
            "An unusually high volume candle (relative volume > threshold) "
            "combined with positive price action may indicate institutional "
            "buying interest and predict short-term continuation."
        ),
        description=(
            "Event-based LONG when relative_volume > rv_threshold AND "
            "close > open (bullish candle body)."
        ),
        default_parameters={"vol_period": 20, "rv_threshold": 2.0},
        parameter_schema={
            "vol_period":   {"type": "int",   "default": 20,  "min": 2,   "doc": "Relative volume baseline period"},
            "rv_threshold": {"type": "float", "default": 2.0, "min": 1.0, "doc": "Relative volume threshold"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["open", "close", "volume"],
        warmup_period=22,
        is_event_based=True,
        notes="rv_threshold 2.0 is not empirically optimized.",
    )

    def __init__(self, vol_period: int = 20, rv_threshold: float = 2.0) -> None:
        super().__init__()
        if vol_period < 2:
            raise ValueError(f"vol_period must be >= 2")
        if rv_threshold < 1.0:
            raise ValueError(f"rv_threshold must be >= 1.0")
        self._period = vol_period
        self._thresh = rv_threshold

    @property
    def parameters(self) -> dict:
        return {"vol_period": self._period, "rv_threshold": self._thresh}

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        volumes = [c.volume for c in candles]
        rv = relative_volume(volumes, self._period)
        if rv is None:
            return None

        last = candles[-1]
        bullish_candle = last.close > last.open
        spike = rv >= self._thresh

        if spike and bullish_candle:
            return Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=last.asset,
                timeframe=last.timeframe,
                direction=SignalDirection.LONG,
                strength=min(rv / (self._thresh * 2), 1.0),
                metadata={
                    "reason": f"volume spike (RV={rv:.2f}x) with bullish candle",
                    "relative_volume": rv,
                    "threshold": self._thresh,
                },
            )
        return None


# ---------------------------------------------------------------------------
# F2 — Volume-Weighted Momentum
# ---------------------------------------------------------------------------

@REGISTRY.register
class VolumeWeightedMomentum(BaseStrategy):
    """
    F2 — Volume-Weighted Momentum: LONG when price momentum (ROC) is positive
    AND volume is elevated above its baseline (relative volume > threshold).
    """

    _info = StrategyInfo(
        strategy_id="VOL_WGT_MOM_001",
        name="Volume-Weighted Momentum",
        version="1.0.0",
        category="volume",
        hypothesis=(
            "Price momentum accompanied by above-average volume may indicate "
            "stronger directional conviction than price momentum alone."
        ),
        description=(
            "Event-based LONG when ROC > roc_threshold AND "
            "relative_volume > rv_threshold (both conditions first met together)."
        ),
        default_parameters={"roc_period": 10, "roc_threshold": 0.5, "vol_period": 20, "rv_threshold": 1.5},
        parameter_schema={
            "roc_period":    {"type": "int",   "default": 10,  "min": 1,   "doc": "ROC lookback period"},
            "roc_threshold": {"type": "float", "default": 0.5, "min": 0.0, "doc": "Minimum ROC %"},
            "vol_period":    {"type": "int",   "default": 20,  "min": 2,   "doc": "Volume baseline period"},
            "rv_threshold":  {"type": "float", "default": 1.5, "min": 1.0, "doc": "Relative volume threshold"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close", "volume"],
        warmup_period=22,
        is_event_based=True,
        notes="Thresholds are not empirically optimized.",
    )

    def __init__(
        self,
        roc_period: int = 10,
        roc_threshold: float = 0.5,
        vol_period: int = 20,
        rv_threshold: float = 1.5,
    ) -> None:
        super().__init__()
        if roc_period <= 0:
            raise ValueError("roc_period must be > 0")
        if roc_threshold < 0:
            raise ValueError("roc_threshold must be >= 0")
        if vol_period < 2:
            raise ValueError("vol_period must be >= 2")
        if rv_threshold < 1.0:
            raise ValueError("rv_threshold must be >= 1.0")
        self._roc_period = roc_period
        self._roc_thresh = roc_threshold
        self._vol_period = vol_period
        self._rv_thresh = rv_threshold
        self._prev_both: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "roc_period": self._roc_period,
            "roc_threshold": self._roc_thresh,
            "vol_period": self._vol_period,
            "rv_threshold": self._rv_thresh,
        }

    @property
    def minimum_candles_required(self) -> int:
        return max(self._roc_period, self._vol_period) + 2

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]

        roc_val = roc(closes, self._roc_period)
        rv = relative_volume(volumes, self._vol_period)

        if roc_val is None or rv is None:
            self._prev_both = None
            return None

        both = roc_val >= self._roc_thresh and rv >= self._rv_thresh

        signal = None
        if self._prev_both is not None and not self._prev_both and both:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "ROC and relative volume both exceed thresholds",
                    "roc": roc_val,
                    "relative_volume": rv,
                    "roc_threshold": self._roc_thresh,
                    "rv_threshold": self._rv_thresh,
                },
            )

        self._prev_both = both
        return signal

    def reset(self) -> None:
        self._prev_both = None


# ---------------------------------------------------------------------------
# F3 — Volume Breakout Confirmation
# ---------------------------------------------------------------------------

@REGISTRY.register
class VolumeBreakoutConfirmation(BaseStrategy):
    """
    F3 — Volume Breakout Confirmation: LONG when price breaks above rolling high
    AND volume confirms (relative volume > threshold).
    """

    _info = StrategyInfo(
        strategy_id="VOL_BREAK_CONF_001",
        name="Volume Breakout Confirmation",
        version="1.0.0",
        category="volume",
        hypothesis=(
            "A price breakout confirmed by above-average volume may be more "
            "reliable than an unconfirmed breakout, as elevated volume suggests "
            "participation beyond normal trading activity."
        ),
        description=(
            "Event-based LONG when close breaks above prior rolling high AND "
            "relative_volume > rv_threshold."
        ),
        default_parameters={"breakout_period": 15, "vol_period": 20, "rv_threshold": 1.5},
        parameter_schema={
            "breakout_period": {"type": "int",   "default": 15,  "min": 2,   "doc": "Price breakout lookback"},
            "vol_period":      {"type": "int",   "default": 20,  "min": 2,   "doc": "Volume baseline period"},
            "rv_threshold":    {"type": "float", "default": 1.5, "min": 1.0, "doc": "Relative volume threshold"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["high", "close", "volume"],
        warmup_period=23,
        is_event_based=True,
        notes="rv_threshold 1.5 is not empirically optimized.",
    )

    def __init__(
        self,
        breakout_period: int = 15,
        vol_period: int = 20,
        rv_threshold: float = 1.5,
    ) -> None:
        super().__init__()
        if breakout_period < 2:
            raise ValueError("breakout_period must be >= 2")
        if vol_period < 2:
            raise ValueError("vol_period must be >= 2")
        if rv_threshold < 1.0:
            raise ValueError("rv_threshold must be >= 1.0")
        self._break_period = breakout_period
        self._vol_period = vol_period
        self._rv_thresh = rv_threshold
        self._prev_above: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "breakout_period": self._break_period,
            "vol_period": self._vol_period,
            "rv_threshold": self._rv_thresh,
        }

    @property
    def minimum_candles_required(self) -> int:
        return max(self._break_period, self._vol_period) + 2

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]

        range_top = rolling_high(highs, self._break_period, shift=1)
        rv = relative_volume(volumes, self._vol_period)

        if range_top is None or rv is None:
            self._prev_above = None
            return None

        above = closes[-1] > range_top
        vol_confirmed = rv >= self._rv_thresh

        signal = None
        if (
            self._prev_above is not None
            and not self._prev_above
            and above
            and vol_confirmed
        ):
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "price breakout confirmed by elevated volume",
                    "close": closes[-1],
                    "range_top": range_top,
                    "relative_volume": rv,
                    "rv_threshold": self._rv_thresh,
                },
            )

        self._prev_above = above
        return signal

    def reset(self) -> None:
        self._prev_above = None
