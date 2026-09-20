"""
ENGINE_VALIDATION_ONLY strategy — deterministic validation strategy for Prompt 03.

⚠️ WARNING ⚠️
━━━━━━━━━━━━━━
This strategy exists SOLELY to exercise all engine execution paths.
It is NOT a trading strategy.
Results produced by this strategy have ZERO research value.
DO NOT use this strategy in Prompt 04+ research.
DO NOT interpret its results as evidence of any edge.

Design:
    - Generates a LONG entry signal every N candles (default: 20).
    - Stop = entry_price × (1 - 0.01)  → 1% below entry.
    - Target = entry_price × (1 + 0.01 × R:R)  → computed from configured R/R.
    - Deterministic: same data → same signals, same order, same trades.

The N=20 cadence is arbitrary. Its only purpose is to create periodic
entries so that stops, targets, gap fills, and ambiguous candles are
exercised during the validation run.
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.core.domain import SignalDirection, Timeframe


class EngineValidationStrategy:
    """
    Deterministic every-N-candles LONG strategy for engine validation.

    This strategy is labelled ENGINE_VALIDATION_ONLY in all output files
    to prevent confusion with real research strategies.

    Usage:
        strategy = EngineValidationStrategy(signal_every_n_candles=20, rr_ratio=3.0)
        signal = strategy.on_candle(candle_df, symbol, timeframe, timestamp)
    """

    NAME = "ENGINE_VALIDATION_ONLY"
    VERSION = "1.0.0"

    def __init__(
        self,
        signal_every_n_candles: int = 20,
        rr_ratio: float = 3.0,
        stop_distance_pct: float = 1.0,
    ) -> None:
        """
        Args:
            signal_every_n_candles: Generate a signal every N candles (default 20).
            rr_ratio:               Reward-to-risk ratio for target calculation.
            stop_distance_pct:      Stop distance as % of entry price (default 1.0%).
        """
        if signal_every_n_candles < 1:
            raise ValueError("signal_every_n_candles must be >= 1")
        if rr_ratio <= 0:
            raise ValueError("rr_ratio must be positive")
        if stop_distance_pct <= 0 or stop_distance_pct >= 100:
            raise ValueError("stop_distance_pct must be in (0, 100)")

        self._n = signal_every_n_candles
        self._rr = rr_ratio
        self._stop_pct = stop_distance_pct / 100.0
        self._candle_count: dict[str, int] = {}  # symbol → count

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def version(self) -> str:
        return self.VERSION

    def on_candle(
        self,
        close_price: float,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
    ) -> dict | None:
        """
        Called by the engine on each closed candle.

        Returns a signal dict if this is a signal candle, else None.

        Signal format:
            {
                "direction": "long",
                "stop_price": float,
                "target_price": float,
                "strength": 1.0,
            }

        Args:
            close_price: Close price of the current candle.
            symbol:      Asset symbol.
            timeframe:   Candle timeframe string.
            timestamp:   Simulation timestamp.

        Returns:
            Signal dict on signal candles, None otherwise.
        """
        key = f"{symbol}_{timeframe}"
        self._candle_count[key] = self._candle_count.get(key, 0) + 1

        if self._candle_count[key] % self._n != 0:
            return None

        # Compute stop and target from close price
        stop_distance = close_price * self._stop_pct
        stop_price = close_price - stop_distance
        target_price = close_price + stop_distance * self._rr

        return {
            "direction": SignalDirection.LONG,
            "stop_price": stop_price,
            "target_price": target_price,
            "strength": 1.0,
            "strategy_name": self.NAME,
        }

    def reset(self) -> None:
        """Reset candle counters. Used between validation runs."""
        self._candle_count.clear()

    @property
    def parameters(self) -> dict:
        """Strategy parameters for metadata recording."""
        return {
            "signal_every_n_candles": self._n,
            "rr_ratio": self._rr,
            "stop_distance_pct": self._stop_pct * 100,
            "WARNING": "ENGINE_VALIDATION_ONLY — not a research strategy",
        }
