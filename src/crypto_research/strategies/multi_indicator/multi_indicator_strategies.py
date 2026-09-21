"""
Group G — Multi-Indicator Confirmation strategies.

G1 — Trend + Momentum + Volume (TREND_MOM_VOL_001).
G2 — Trend + Volatility + Momentum (TREND_VOL_MOM_001).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import atr, bb_width, ema, relative_volume, roc, rsi
from crypto_research.strategies.registry import REGISTRY


# ---------------------------------------------------------------------------
# G1 — Trend + Momentum + Volume
# ---------------------------------------------------------------------------

@REGISTRY.register
class TrendMomentumVolume(BaseStrategy):
    """
    G1 — Trend + Momentum + Volume confirmation.
    Three independent dimensions must align: trend (EMA), momentum (ROC), volume (RV).
    Tests whether multi-dimensional confirmation improves signal selectivity.
    """

    _info = StrategyInfo(
        strategy_id="TREND_MOM_VOL_001",
        name="Trend + Momentum + Volume Confirmation",
        version="1.0.0",
        category="multi_indicator",
        hypothesis=(
            "Combining an independent trend condition (close > EMA), momentum condition "
            "(ROC > threshold), and volume confirmation (relative volume > threshold) "
            "may produce higher-quality signals than any single indicator."
        ),
        description=(
            "Event-based LONG when: close > EMA(ema_period) AND ROC > roc_threshold "
            "AND relative_volume > rv_threshold — all on the same candle (first occurrence)."
        ),
        default_parameters={
            "ema_period": 21,
            "roc_period": 10,
            "roc_threshold": 0.5,
            "vol_period": 20,
            "rv_threshold": 1.5,
        },
        parameter_schema={
            "ema_period":    {"type": "int",   "default": 21,  "min": 2,   "doc": "Trend EMA period"},
            "roc_period":    {"type": "int",   "default": 10,  "min": 1,   "doc": "ROC period"},
            "roc_threshold": {"type": "float", "default": 0.5, "min": 0.0, "doc": "Minimum ROC %"},
            "vol_period":    {"type": "int",   "default": 20,  "min": 2,   "doc": "Volume baseline period"},
            "rv_threshold":  {"type": "float", "default": 1.5, "min": 1.0, "doc": "Relative volume threshold"},
        },
        supported_timeframes=["15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close", "volume"],
        warmup_period=24,
        is_event_based=True,
        notes="Multi-indicator combination hypothesis — not individually optimized.",
    )

    def __init__(
        self,
        ema_period: int = 21,
        roc_period: int = 10,
        roc_threshold: float = 0.5,
        vol_period: int = 20,
        rv_threshold: float = 1.5,
    ) -> None:
        super().__init__()
        if ema_period <= 0:
            raise ValueError("ema_period must be > 0")
        if roc_period <= 0:
            raise ValueError("roc_period must be > 0")
        if roc_threshold < 0:
            raise ValueError("roc_threshold must be >= 0")
        if vol_period < 2:
            raise ValueError("vol_period must be >= 2")
        if rv_threshold < 1.0:
            raise ValueError("rv_threshold must be >= 1.0")
        self._ema_period = ema_period
        self._roc_period = roc_period
        self._roc_thresh = roc_threshold
        self._vol_period = vol_period
        self._rv_thresh = rv_threshold
        self._prev_all_align: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "ema_period": self._ema_period,
            "roc_period": self._roc_period,
            "roc_threshold": self._roc_thresh,
            "vol_period": self._vol_period,
            "rv_threshold": self._rv_thresh,
        }

    @property
    def minimum_candles_required(self) -> int:
        return max(self._ema_period, self._roc_period, self._vol_period) + 2

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]

        ema_val = ema(closes, self._ema_period)
        roc_val = roc(closes, self._roc_period)
        rv = relative_volume(volumes, self._vol_period)

        if ema_val is None or roc_val is None or rv is None:
            self._prev_all_align = None
            return None

        all_align = (
            closes[-1] > ema_val
            and roc_val >= self._roc_thresh
            and rv >= self._rv_thresh
        )

        signal = None
        if self._prev_all_align is not None and not self._prev_all_align and all_align:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "trend, momentum, and volume all aligned bullish",
                    "close": closes[-1],
                    "ema": ema_val,
                    "roc": roc_val,
                    "relative_volume": rv,
                },
            )

        self._prev_all_align = all_align
        return signal

    def reset(self) -> None:
        self._prev_all_align = None


# ---------------------------------------------------------------------------
# G2 — Trend + Volatility + Momentum
# ---------------------------------------------------------------------------

@REGISTRY.register
class TrendVolatilityMomentum(BaseStrategy):
    """
    G2 — Trend + Volatility + Momentum.
    Tests whether confirming trend with volatility regime AND RSI momentum
    improves selectivity over single indicators.
    """

    _info = StrategyInfo(
        strategy_id="TREND_VOL_MOM_001",
        name="Trend + Volatility + Momentum Confirmation",
        version="1.0.0",
        category="multi_indicator",
        hypothesis=(
            "Combining trend bias (close > EMA), volatility regime (ATR > avg ATR threshold), "
            "and RSI momentum (RSI > level) may produce signals with higher directional conviction."
        ),
        description=(
            "Event-based LONG when: close > EMA AND ATR elevated AND RSI > rsi_level "
            "(first candle where all three conditions align)."
        ),
        default_parameters={
            "ema_period": 21,
            "atr_period": 14,
            "atr_avg_period": 20,
            "atr_multiplier": 1.1,
            "rsi_period": 14,
            "rsi_level": 55.0,
        },
        parameter_schema={
            "ema_period":     {"type": "int",   "default": 21,   "min": 2,    "doc": "Trend EMA period"},
            "atr_period":     {"type": "int",   "default": 14,   "min": 2,    "doc": "ATR period"},
            "atr_avg_period": {"type": "int",   "default": 20,   "min": 2,    "doc": "ATR avg period"},
            "atr_multiplier": {"type": "float", "default": 1.1,  "min": 1.0,  "doc": "ATR expansion threshold"},
            "rsi_period":     {"type": "int",   "default": 14,   "min": 2,    "doc": "RSI period"},
            "rsi_level":      {"type": "float", "default": 55.0, "min": 0.0,  "max": 100.0, "doc": "RSI threshold"},
        },
        supported_timeframes=["15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["high", "low", "close"],
        warmup_period=40,
        is_event_based=True,
        notes="Multi-indicator combination hypothesis — not individually optimized.",
    )

    def __init__(
        self,
        ema_period: int = 21,
        atr_period: int = 14,
        atr_avg_period: int = 20,
        atr_multiplier: float = 1.1,
        rsi_period: int = 14,
        rsi_level: float = 55.0,
    ) -> None:
        super().__init__()
        if ema_period <= 0:
            raise ValueError("ema_period must be > 0")
        if atr_period < 2:
            raise ValueError("atr_period must be >= 2")
        if atr_avg_period < 2:
            raise ValueError("atr_avg_period must be >= 2")
        if atr_multiplier < 1.0:
            raise ValueError("atr_multiplier must be >= 1.0")
        if rsi_period < 2:
            raise ValueError("rsi_period must be >= 2")
        if not (0.0 < rsi_level < 100.0):
            raise ValueError(f"rsi_level must be in (0, 100), got {rsi_level}")
        self._ema_p = ema_period
        self._atr_p = atr_period
        self._atr_avg = atr_avg_period
        self._atr_mult = atr_multiplier
        self._rsi_p = rsi_period
        self._rsi_lvl = rsi_level
        self._prev_all_align: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "ema_period": self._ema_p,
            "atr_period": self._atr_p,
            "atr_avg_period": self._atr_avg,
            "atr_multiplier": self._atr_mult,
            "rsi_period": self._rsi_p,
            "rsi_level": self._rsi_lvl,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._atr_p + self._atr_avg + self._rsi_p

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        ema_val = ema(closes, self._ema_p)
        current_atr = atr(highs, lows, closes, self._atr_p)
        rsi_val = rsi(closes, self._rsi_p)

        if ema_val is None or current_atr is None or rsi_val is None:
            self._prev_all_align = None
            return None

        # ATR average
        if len(candles) < self._atr_p + self._atr_avg:
            self._prev_all_align = None
            return None

        atr_vals: list[float] = []
        for i in range(self._atr_avg):
            idx = len(candles) - self._atr_avg + i + 1
            v = atr(highs[:idx], lows[:idx], closes[:idx], self._atr_p)
            if v is not None:
                atr_vals.append(v)

        if not atr_vals:
            self._prev_all_align = None
            return None

        avg_atr = sum(atr_vals) / len(atr_vals)
        atr_elevated = current_atr > self._atr_mult * avg_atr

        all_align = (
            closes[-1] > ema_val
            and atr_elevated
            and rsi_val >= self._rsi_lvl
        )

        signal = None
        if self._prev_all_align is not None and not self._prev_all_align and all_align:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "trend, volatility expansion, and RSI momentum all aligned",
                    "close": closes[-1],
                    "ema": ema_val,
                    "atr": current_atr,
                    "avg_atr": avg_atr,
                    "rsi": rsi_val,
                },
            )

        self._prev_all_align = all_align
        return signal

    def reset(self) -> None:
        self._prev_all_align = None
