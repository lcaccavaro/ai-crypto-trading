"""
Group H — Market Structure strategies.

H1 — Higher-High / Higher-Low Structure (HH_HL_001).
H2 — Volatility-Regime Conditional Strategy (VOL_REGIME_001).
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import Candle, Signal, SignalDirection, StrategyInfo
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.indicators import atr, bb_width
from crypto_research.strategies.registry import REGISTRY


# ---------------------------------------------------------------------------
# H1 — Higher-High / Higher-Low Structure
# ---------------------------------------------------------------------------

@REGISTRY.register
class HHHLStructure(BaseStrategy):
    """
    H1 — Higher-High / Higher-Low Structure.
    Detects when price forms a bullish market structure: the current candle's
    high exceeds the previous n-candle high, and the current candle's low is
    higher than the low of n candles ago.
    Uses ONLY completed historical observations.
    """

    _info = StrategyInfo(
        strategy_id="HH_HL_001",
        name="Higher-High / Higher-Low Structure",
        version="1.0.0",
        category="market_structure",
        hypothesis=(
            "A market forming consecutively higher highs and higher lows may "
            "indicate an emerging bullish price structure. This hypothesis tests "
            "whether simple structure detection has predictive value."
        ),
        description=(
            "Event-based LONG when: current_high > max(highs[-lookback:-1]) AND "
            "current_low > min(lows[-lookback:-1]). "
            "Uses only completed candles — no future information."
        ),
        default_parameters={"lookback": 5},
        parameter_schema={
            "lookback": {"type": "int", "default": 5, "min": 2, "doc": "Candles for HH/HL detection"},
        },
        supported_timeframes=["5m", "15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["high", "low"],
        warmup_period=7,
        is_event_based=True,
        notes="Structure detection uses prior window only (PIT safe).",
    )

    def __init__(self, lookback: int = 5) -> None:
        super().__init__()
        if lookback < 2:
            raise ValueError(f"lookback must be >= 2, got {lookback}")
        self._lookback = lookback
        self._prev_hh_hl: bool | None = None

    @property
    def parameters(self) -> dict:
        return {"lookback": self._lookback}

    @property
    def minimum_candles_required(self) -> int:
        return self._lookback + 2

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        # Prior window (exclude current candle)
        prior_highs = highs[-(self._lookback + 1):-1]
        prior_lows = lows[-(self._lookback + 1):-1]

        if len(prior_highs) < self._lookback:
            self._prev_hh_hl = None
            return None

        prior_high = max(prior_highs)
        prior_low = min(prior_lows)

        hh = highs[-1] > prior_high
        hl = lows[-1] > prior_low

        hh_hl = hh and hl

        signal = None
        if self._prev_hh_hl is not None and not self._prev_hh_hl and hh_hl:
            signal = Signal(
                timestamp=timestamp,
                strategy_name=self._info.strategy_id,
                asset=candles[-1].asset,
                timeframe=candles[-1].timeframe,
                direction=SignalDirection.LONG,
                strength=1.0,
                metadata={
                    "reason": "higher-high and higher-low structure confirmed",
                    "current_high": highs[-1],
                    "current_low": lows[-1],
                    "prior_high": prior_high,
                    "prior_low": prior_low,
                    "lookback": self._lookback,
                },
            )

        self._prev_hh_hl = hh_hl
        return signal

    def reset(self) -> None:
        self._prev_hh_hl = None


# ---------------------------------------------------------------------------
# H2 — Volatility-Regime Conditional Strategy
# ---------------------------------------------------------------------------

@REGISTRY.register
class VolatilityRegimeConditional(BaseStrategy):
    """
    H2 — Volatility-Regime Conditional.
    Uses volatility regime (BB width classification) to conditionally apply
    breakout behavior: only generates breakout signals during high-volatility
    regime. In low-volatility, no signals are generated.

    Regime classification uses ONLY historical data (PIT safe).
    No future volatility is used.
    """

    _info = StrategyInfo(
        strategy_id="VOL_REGIME_001",
        name="Volatility-Regime Conditional Strategy",
        version="1.0.0",
        category="market_structure",
        hypothesis=(
            "Breakout signals may be more reliable during high-volatility regimes "
            "(BB width > expansion threshold) and unreliable during compression. "
            "Conditioning signal generation on volatility regime may improve selectivity."
        ),
        description=(
            "Only generates LONG breakout signals (close > prior high) when "
            "BB width exceeds expansion_threshold (high volatility regime). "
            "In low/medium volatility: NO_SIGNAL."
        ),
        default_parameters={
            "bb_period": 20,
            "bb_std": 2.0,
            "expansion_threshold": 0.04,
            "breakout_period": 15,
        },
        parameter_schema={
            "bb_period":           {"type": "int",   "default": 20,   "min": 5,   "doc": "BB period"},
            "bb_std":              {"type": "float", "default": 2.0,  "min": 0.1, "doc": "BB std"},
            "expansion_threshold": {"type": "float", "default": 0.04, "min": 0.0, "doc": "BB width expansion threshold"},
            "breakout_period":     {"type": "int",   "default": 15,   "min": 2,   "doc": "Price breakout lookback"},
        },
        supported_timeframes=["15m", "30m", "1h", "4h"],
        supported_sides=["long"],
        required_features=["high", "close"],
        warmup_period=22,
        is_event_based=True,
        notes=(
            "Volatility regime uses only historical BB width — no future values. "
            "expansion_threshold 0.04 is not empirically optimized."
        ),
    )

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        expansion_threshold: float = 0.04,
        breakout_period: int = 15,
    ) -> None:
        super().__init__()
        if bb_period <= 0:
            raise ValueError("bb_period must be > 0")
        if bb_std <= 0:
            raise ValueError("bb_std must be > 0")
        if expansion_threshold < 0:
            raise ValueError("expansion_threshold must be >= 0")
        if breakout_period < 2:
            raise ValueError("breakout_period must be >= 2")
        self._bb_period = bb_period
        self._bb_std = bb_std
        self._exp_thresh = expansion_threshold
        self._break_period = breakout_period
        self._prev_above: bool | None = None

    @property
    def parameters(self) -> dict:
        return {
            "bb_period": self._bb_period,
            "bb_std": self._bb_std,
            "expansion_threshold": self._exp_thresh,
            "breakout_period": self._break_period,
        }

    @property
    def minimum_candles_required(self) -> int:
        return max(self._bb_period, self._break_period) + 2

    def _compute_signal(self, candles: list[Candle], timestamp: datetime) -> Signal | None:
        highs = [c.high for c in candles]
        closes = [c.close for c in candles]

        width = bb_width(closes, self._bb_period, self._bb_std)

        # Only active in high-volatility regime
        if width is None or width < self._exp_thresh:
            self._prev_above = None
            return None  # NOT_READY or low-volatility regime

        from crypto_research.strategies.indicators import rolling_high
        range_top = rolling_high(highs, self._break_period, shift=1)

        if range_top is None:
            self._prev_above = None
            return None

        above = closes[-1] > range_top

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
                    "reason": "breakout during high-volatility regime",
                    "close": closes[-1],
                    "range_top": range_top,
                    "bb_width": width,
                    "expansion_threshold": self._exp_thresh,
                },
            )

        self._prev_above = above
        return signal

    def reset(self) -> None:
        self._prev_above = None
