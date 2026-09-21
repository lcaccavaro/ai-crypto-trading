"""
E1 — ATR Expansion (ATR_EXPAND_001).
E2 — Volatility Compression → Expansion (VOL_COMPRESS_001).
E3 — Bollinger Band Width Expansion (BB_WIDTH_001).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import atr, bb_width
from crypto_research.strategies.registry import REGISTRY


# ---------------------------------------------------------------------------
# E1 — ATR Expansion
# ---------------------------------------------------------------------------

@REGISTRY.register
class ATRExpansion(BaseStrategy):
    """
    E1 — ATR Expansion: LONG when ATR crosses above its rolling average,
    indicating volatility expansion, combined with bullish price action
    (close > prior close).
    """

    _info = StrategyInfo(
        strategy_id="ATR_EXPAND_001",
        name="ATR Expansion",
        version="1.0.0",
        category="volatility",
        hypothesis=(
            "An unusual increase in ATR (ATR > avg_ATR) combined with positive "
            "price action may indicate the start of a directional volatile move."
        ),
        description=(
            "Event-based LONG when ATR crosses above its rolling average "
            "AND close > prior close (bullish direction)."
        ),
        default_parameters={"atr_period": 14, "avg_period": 20, "multiplier": 1.2},
        parameter_schema={
            "atr_period":  {"type": "int",   "default": 14,  "min": 2,   "doc": "ATR period"},
            "avg_period":  {"type": "int",   "default": 20,  "min": 2,   "doc": "Rolling avg of ATR period"},
            "multiplier":  {"type": "float", "default": 1.2, "min": 1.0, "doc": "ATR expansion threshold"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["high", "low", "close"],
        warmup_period=36,
        is_event_based=True,
        notes="Threshold 1.2x is not empirically optimized.",
    )

    def __init__(self, atr_period: int = 14, avg_period: int = 20, multiplier: float = 1.2) -> None:
        super().__init__()
        if atr_period < 2:
            raise ValueError(f"atr_period must be >= 2")
        if avg_period < 2:
            raise ValueError(f"avg_period must be >= 2")
        if multiplier < 1.0:
            raise ValueError(f"multiplier must be >= 1.0")
        self._atr = atr_period
        self._avg = avg_period
        self._mult = multiplier
        self._prev_atr_elevated: bool | None = None

    @property
    def parameters(self) -> dict:
        return {"atr_period": self._atr, "avg_period": self._avg, "multiplier": self._mult}

    @property
    def minimum_candles_required(self) -> int:
        return self._atr + self._avg + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]

        current_atr = atr(highs, lows, closes, self._atr)
        if current_atr is None or len(candles) < self._atr + self._avg:
            self._prev_atr_elevated = None
            return None

        # Compute avg ATR over last avg_period windows
        atr_vals: list[float] = []
        for i in range(self._avg):
            idx = len(candles) - self._avg + i + 1
            v = atr(highs[:idx], lows[:idx], closes[:idx], self._atr)
            if v is not None:
                atr_vals.append(v)

        if not atr_vals:
            self._prev_atr_elevated = None
            return None

        avg_atr = sum(atr_vals) / len(atr_vals)
        atr_elevated = current_atr > self._mult * avg_atr
        bullish = closes[-1] > closes[-2]

        signal = None
        if (
            self._prev_atr_elevated is not None
            and not self._prev_atr_elevated
            and atr_elevated
            and bullish
        ):
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "ATR expanded above rolling average with bullish price action",
                    "atr": current_atr,
                    "avg_atr": avg_atr,
                    "multiplier": self._mult,
                },
            )

        self._prev_atr_elevated = atr_elevated
        return signal

    def reset(self) -> None:
        self._prev_atr_elevated = None


# ---------------------------------------------------------------------------
# E2 — Volatility Compression → Expansion
# ---------------------------------------------------------------------------

@REGISTRY.register
class VolatilityCompression(BaseStrategy):
    """
    E2 — Volatility Compression → Expansion.
    Detects a period of compressed BB width followed by expansion.
    Arms when BB width drops below compression_threshold.
    Fires LONG when BB width expands above expansion_threshold with bullish price.
    """

    _info = StrategyInfo(
        strategy_id="VOL_COMPRESS_001",
        name="Volatility Compression to Expansion",
        version="1.0.0",
        category="volatility",
        hypothesis=(
            "A period of low volatility (compressed Bollinger Band width) "
            "followed by an expansion may signal the start of a directional move."
        ),
        description=(
            "Arms when BB width < compression_threshold. Fires LONG when "
            "BB width > expansion_threshold AND close > prior close."
        ),
        default_parameters={
            "bb_period": 20,
            "bb_std": 2.0,
            "compression_threshold": 0.02,
            "expansion_threshold": 0.04,
        },
        parameter_schema={
            "bb_period":              {"type": "int",   "default": 20,   "min": 5,   "doc": "BB period"},
            "bb_std":                 {"type": "float", "default": 2.0,  "min": 0.1, "doc": "BB std multiplier"},
            "compression_threshold":  {"type": "float", "default": 0.02, "min": 0.0, "doc": "BB width arm level"},
            "expansion_threshold":    {"type": "float", "default": 0.04, "min": 0.0, "doc": "BB width fire level"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=21,
        is_event_based=True,
        notes="Thresholds are not empirically optimized.",
    )

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        compression_threshold: float = 0.02,
        expansion_threshold: float = 0.04,
    ) -> None:
        super().__init__()
        if bb_period <= 0:
            raise ValueError(f"bb_period must be > 0")
        if bb_std <= 0:
            raise ValueError(f"bb_std must be > 0")
        if compression_threshold < 0:
            raise ValueError(f"compression_threshold must be >= 0")
        if expansion_threshold <= compression_threshold:
            raise ValueError(f"expansion_threshold must be > compression_threshold")
        self._period = bb_period
        self._std = bb_std
        self._compress = compression_threshold
        self._expand = expansion_threshold
        self._armed: bool = False

    @property
    def parameters(self) -> dict:
        return {
            "bb_period": self._period,
            "bb_std": self._std,
            "compression_threshold": self._compress,
            "expansion_threshold": self._expand,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]
        width = bb_width(closes, self._period, self._std)

        if width is None:
            return None

        if width < self._compress:
            self._armed = True

        if self._armed and width > self._expand and closes[-1] > closes[-2]:
            self._armed = False
            return Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "BB width expanded after compression with bullish price action",
                    "bb_width": width,
                    "compress_threshold": self._compress,
                    "expand_threshold": self._expand,
                },
            )

        return None

    def reset(self) -> None:
        self._armed = False


# ---------------------------------------------------------------------------
# E3 — Bollinger Band Width Expansion
# ---------------------------------------------------------------------------

@REGISTRY.register
class BBWidthExpansion(BaseStrategy):
    """
    E3 — BB Width Expansion.
    Fires LONG when BB width crosses above its rolling average (expansion event)
    combined with bullish price action.
    """

    _info = StrategyInfo(
        strategy_id="BB_WIDTH_001",
        name="Bollinger Band Width Expansion",
        version="1.0.0",
        category="volatility",
        hypothesis=(
            "When Bollinger Band width expands above its rolling average, "
            "this may indicate increasing volatility that could precede "
            "a directional move."
        ),
        description=(
            "Event-based LONG when BB width crosses above width_avg_multiplier * "
            "rolling average of BB width, with bullish price action."
        ),
        default_parameters={
            "bb_period": 20,
            "bb_std": 2.0,
            "avg_period": 20,
            "width_avg_multiplier": 1.3,
        },
        parameter_schema={
            "bb_period":           {"type": "int",   "default": 20,  "min": 5,   "doc": "BB period"},
            "bb_std":              {"type": "float", "default": 2.0, "min": 0.1, "doc": "BB std"},
            "avg_period":          {"type": "int",   "default": 20,  "min": 2,   "doc": "BB width average period"},
            "width_avg_multiplier":{"type": "float", "default": 1.3, "min": 1.0, "doc": "Expansion multiplier"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["close"],
        warmup_period=42,
        is_event_based=True,
        notes="width_avg_multiplier 1.3 is not empirically optimized.",
    )

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        avg_period: int = 20,
        width_avg_multiplier: float = 1.3,
    ) -> None:
        super().__init__()
        if bb_period <= 0:
            raise ValueError("bb_period must be > 0")
        if bb_std <= 0:
            raise ValueError("bb_std must be > 0")
        if avg_period < 2:
            raise ValueError("avg_period must be >= 2")
        if width_avg_multiplier < 1.0:
            raise ValueError("width_avg_multiplier must be >= 1.0")
        self._bb_period = bb_period
        self._bb_std = bb_std
        self._avg_period = avg_period
        self._mult = width_avg_multiplier
        self._prev_elevated: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "bb_period": self._bb_period,
            "bb_std": self._bb_std,
            "avg_period": self._avg_period,
            "width_avg_multiplier": self._mult,
        }

    @property
    def minimum_candles_required(self) -> int:
        return self._bb_period + self._avg_period + 1

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        closes = [c.close for c in candles]

        current_width = bb_width(closes, self._bb_period, self._bb_std)
        if current_width is None:
            self._prev_elevated = None
            return None

        # Rolling average of BB width
        widths: list[float] = []
        for i in range(self._avg_period):
            idx = len(closes) - self._avg_period + i + 1
            w = bb_width(closes[:idx], self._bb_period, self._bb_std)
            if w is not None:
                widths.append(w)

        if not widths:
            self._prev_elevated = None
            return None

        avg_width = sum(widths) / len(widths)
        elevated = current_width > self._mult * avg_width
        bullish = closes[-1] > closes[-2]

        signal = None
        if self._prev_elevated is not None and not self._prev_elevated and elevated and bullish:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "BB width expanded above rolling average with bullish price",
                    "bb_width": current_width,
                    "avg_width": avg_width,
                    "multiplier": self._mult,
                },
            )

        self._prev_elevated = elevated
        return signal

    def reset(self) -> None:
        self._prev_elevated = None
